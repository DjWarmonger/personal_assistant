import sqlite3
import threading
import time
from typing import Optional, Tuple, List, Union, Dict
from datetime import datetime, timezone
from enum import Enum
from abc import ABC, abstractmethod

from tz_common.logs import log
from tz_common.timed_storage import TimedStorage
from tz_common import CustomUUID

from .utils import Utils

# TODO: Split into cache key utils and db handler?

class ObjectType(Enum):
	BLOCK = "block"
	PAGE = "page"
	DATABASE = "database"
	SEARCH_RESULTS = "search"
	DATABASE_QUERY_RESULTS = "database_query"

# TODO: Convert parent "type": "database_id" to "database" : https://developers.notion.com/reference/page

class BlockCache(TimedStorage):

	def __init__(self,
			  db_path: str = 'block_cache.db',
			  load_from_disk: bool = False,
			  run_on_start: bool = False):
		super().__init__(period_ms=3000, run_on_start=run_on_start)

		self.db_path = db_path
		self.save_enabled = run_on_start

		self.conn = sqlite3.connect(':memory:', check_same_thread=False)
		self.cursor = self.conn.cursor()
		self.lock = threading.RLock()

		if load_from_disk:
			self.load_from_disk()
		self.create_tables()

		# TODO: Set to low value for testing
		self.max_size = 64 * 1024 * 1024  # 64 MB in bytes

		if run_on_start:
			self.start_periodic_save()


	def create_cache_key(self, uuid_str: str, object_type: ObjectType) -> str:
		# Allow non-UUID strings for search/query keys that might not be UUIDs themselves
		if object_type in [ObjectType.SEARCH_RESULTS, ObjectType.DATABASE_QUERY_RESULTS]:
			# For these types, uuid_str might be a composite key, not a pure UUID
			# We assume it's already in the desired format for the key part
			return uuid_str 
		else:
			uuid_obj = CustomUUID.from_string(uuid_str)
			return str(uuid_obj)


	def create_search_results_cache_key(self, query: str, filter_str: Optional[str] = None, start_cursor: Optional[CustomUUID] = None) -> str:
		key = query
		if filter_str is not None:
			key += f":{filter_str}"
		if start_cursor is not None:
			key += f":{str(start_cursor)}"
		# Pass the composite key directly to create_cache_key for SEARCH_RESULTS type
		return self.create_cache_key(key, ObjectType.SEARCH_RESULTS)


	def create_database_query_results_cache_key(self, database_id: CustomUUID, filter_str: Optional[str] = None, start_cursor: Optional[CustomUUID] = None) -> str:
		key = str(database_id)

		if filter_str is not None:
			key += f":{filter_str}"

		if start_cursor is not None:
			key += f":{str(start_cursor)}"
		# Pass the composite key directly to create_cache_key for DATABASE_QUERY_RESULTS type
		return self.create_cache_key(key, ObjectType.DATABASE_QUERY_RESULTS)


	def create_tables(self):
		with self.lock:
			# Create block_cache table if it doesn't exist

			# timestamp = last_edited_time

			self.cursor.execute('''
				CREATE TABLE IF NOT EXISTS block_cache (
					cache_key TEXT NOT NULL,
					object_type TEXT NOT NULL,
					content TEXT,
					timestamp TEXT,
					ttl INTEGER,
					PRIMARY KEY (cache_key, object_type)
				)
			''')
			
			# Create block_relationships table if it doesn't exist
			self.cursor.execute('''
				CREATE TABLE IF NOT EXISTS block_relationships (
					parent_key TEXT,
					child_key TEXT,
					PRIMARY KEY (parent_key, child_key),
					FOREIGN KEY (parent_key) REFERENCES block_cache(cache_key),
					FOREIGN KEY (child_key) REFERENCES block_cache(cache_key)
				)
			''')

			self.cursor.execute('''
				CREATE TABLE IF NOT EXISTS children_fetched_for_block (
					cache_key TEXT PRIMARY KEY
				)
			''')
			
			# Create cache_metrics table to track hits and misses
			self.cursor.execute('''
				CREATE TABLE IF NOT EXISTS cache_metrics (
					metric_type TEXT PRIMARY KEY,
					count INTEGER DEFAULT 0
				)
			''')
			
			# Initialize metrics if they don't exist
			self.cursor.execute('''
				INSERT OR IGNORE INTO cache_metrics (metric_type, count)
				VALUES ('hits', 0)
			''')
			
			self.cursor.execute('''
				INSERT OR IGNORE INTO cache_metrics (metric_type, count)
				VALUES ('misses_not_found', 0)
			''')
			
			self.cursor.execute('''
				INSERT OR IGNORE INTO cache_metrics (metric_type, count)
				VALUES ('misses_expired', 0)
			''')
			
			self.conn.commit()
			self.set_dirty()


	def _increment_metric(self, metric_type: str):
		with self.lock:
			self.cursor.execute('''
				UPDATE cache_metrics
				SET count = count + 1
				WHERE metric_type = ?
			''', (metric_type,))
			self.conn.commit()
			self.set_dirty()


	def _add_block_internal(self, cache_key: str, object_type: ObjectType, content: str, ttl: Optional[int] = None, parent_key: Optional[str] = None):
		now = Utils.get_current_time_isoformat()

		content = str(content)
		
		with self.lock:
			# Check if the cache key already exists
			self.cursor.execute('SELECT 1 FROM block_cache WHERE cache_key = ? AND object_type = ?', (cache_key, object_type.value))
			exists = self.cursor.fetchone() is not None
			
			self.cursor.execute('''
				INSERT OR REPLACE INTO block_cache (cache_key, object_type, content, timestamp, ttl)
				VALUES (?, ?, ?, ?, ?)
			''', (cache_key, object_type.value, content, now, ttl))
			
			if parent_key:
				self.cursor.execute('SELECT 1 FROM block_relationships WHERE parent_key = ? AND child_key = ?', (parent_key, cache_key))
				relationship_exists = self.cursor.fetchone() is not None
				
				self.cursor.execute('''
					INSERT OR IGNORE INTO block_relationships (parent_key, child_key)
					VALUES (?, ?)
				''', (parent_key, cache_key))
			
			self.conn.commit()
			self.set_dirty()
		
		if parent_key:
			if relationship_exists:
				pass
				#log.debug(f"Updating relationship: {parent_key} -> {cache_key}")
			else:
				log.debug(f"Adding relationship: {parent_key} -> {cache_key}")
		
		# FIXME: Do not print if content is identical?
		#log.debug(f'{"Updated block in" if exists else "Added block to"} cache: {cache_key}')


	def add_block(self, uuid: CustomUUID, content: str, ttl: Optional[int] = None, parent_uuid: Optional[CustomUUID] = None, parent_type: ObjectType = ObjectType.BLOCK):

		cache_key = self.create_cache_key(str(uuid), ObjectType.BLOCK)

		parent_key = self.create_cache_key(str(parent_uuid), parent_type) if parent_uuid else None
		self._add_block_internal(cache_key, ObjectType.BLOCK, content, ttl, parent_key)


	def add_page(self, uuid: CustomUUID, content: str, ttl: Optional[int] = None):
		cache_key = self.create_cache_key(str(uuid), ObjectType.PAGE)
		self._add_block_internal(cache_key, ObjectType.PAGE, content, ttl)


	def add_database(self, uuid: CustomUUID, content: str, ttl: Optional[int] = None):
		cache_key = self.create_cache_key(str(uuid), ObjectType.DATABASE)
		self._add_block_internal(cache_key, ObjectType.DATABASE, content, ttl)


	def add_search_results(self,
						query: str,
						content: str,
						filter_str: Optional[str] = None,
						start_cursor: Optional[CustomUUID] = None,
						ttl: Optional[int] = None):

		# TODO: Use ttl for search results?

		cache_key = self.create_search_results_cache_key(query, filter_str, start_cursor)
		self._add_block_internal(cache_key, ObjectType.SEARCH_RESULTS, content, ttl)


	def add_database_query_results(self,
								database_id: Union[str, CustomUUID],
								content: str,
								filter_str: Optional[str] = None,
								start_cursor: Optional[Union[str, CustomUUID]] = None,
								ttl: Optional[int] = None):

		# Convert database_id to CustomUUID if it's a string
		if isinstance(database_id, str):
			db_uuid = CustomUUID.from_string(database_id)
		else:
			db_uuid = database_id
		
		# Convert start_cursor to CustomUUID if it's a string
		start_cursor_uuid = None
		if start_cursor is not None:
			if isinstance(start_cursor, str):
				start_cursor_uuid = CustomUUID.from_string(start_cursor)
			else:
				start_cursor_uuid = start_cursor

		cache_key = self.create_database_query_results_cache_key(db_uuid, filter_str, start_cursor_uuid)
		self._add_block_internal(cache_key, ObjectType.DATABASE_QUERY_RESULTS, content, ttl)


	def _invalidate_block_recursive(self, cache_key: str):

		log.flow(f"Invalidating block {cache_key} and its children recursively")

		child_keys = []
		with self.lock:

			# TODO: Do not invalidate children pages, only blocks
			
			# Find and recursively delete all child blocks
			self.cursor.execute('SELECT child_key FROM block_relationships WHERE parent_key = ?', (cache_key,))
			child_keys = self.cursor.fetchall()
			
			# Delete the current block
			self.cursor.execute('DELETE FROM block_cache WHERE cache_key = ?', (cache_key,))
			
			# Remove the relationships for this block
			self.cursor.execute('DELETE FROM block_relationships WHERE parent_key = ? OR child_key = ?', (cache_key, cache_key))

			self.remove_children_fetched_for_block(cache_key)
			
			self.conn.commit()
			self.set_dirty()

		for (child_key,) in child_keys:
			# FIXME: Never printed
			log.debug(f"Invalidating child {child_key}")
			self._invalidate_block_recursive(child_key)


	def _invalidate_parent_search_or_query(self, cache_key: str):

		log.flow(f"Invalidating parents of block {cache_key}")

		with self.lock:
			# Find and delete all parent blocks that have this block as a child
			self.cursor.execute('SELECT parent_key FROM block_relationships WHERE child_key = ?', (cache_key,))
			parent_keys = self.cursor.fetchall()

			# Filter parent keys that contain "search" or "database_query"
			filtered_parent_keys = [parent_key for (parent_key,) in parent_keys if
				ObjectType.SEARCH_RESULTS.value in parent_key or
				ObjectType.DATABASE_QUERY_RESULTS.value in parent_key]

			# Remove the relationships for this block only for filtered parent keys
			for parent_key in filtered_parent_keys:
				self.cursor.execute('DELETE FROM block_relationships WHERE parent_key = ? AND child_key = ?', (parent_key, cache_key))
			
			self.conn.commit()
			self.set_dirty()

		for (parent_key,) in filtered_parent_keys:
			log.debug(f"Invalidating parent {parent_key}")
			self._invalidate_block_recursive(parent_key)


	def check_if_expired(self, cache_key: str, object_type: ObjectType, last_update_time: str) -> bool:

		with self.lock:
			self.cursor.execute('SELECT timestamp FROM block_cache WHERE cache_key = ? AND object_type = ?', (cache_key, object_type.value))
			result = self.cursor.fetchone()
			if result:
				return result[0] < last_update_time
			else:
				log.debug(f"Item {cache_key} not found in cache")
				return False


	def invalidate_block_if_expired(self, uuid: CustomUUID, last_update_time: str) -> bool:
		cache_key = self.create_cache_key(str(uuid), ObjectType.BLOCK)

		# First check if the block exists at all
		with self.lock:
			self.cursor.execute('SELECT 1 FROM block_cache WHERE cache_key = ? AND object_type = ?', (cache_key, ObjectType.BLOCK.value))
			exists = self.cursor.fetchone() is not None
		
		if not exists:
			# Block doesn't exist, count as a miss
			self._increment_metric('misses_not_found')
			return False

		expired = self.check_if_expired(cache_key, ObjectType.BLOCK, last_update_time)

		if expired:
			# Block exists but is expired, count as a miss_expired
			self._increment_metric('misses_expired')
			self._invalidate_block_recursive(cache_key)
			log.debug(f"Invalidating item {cache_key} and its children due to expiration")
		else:
			pass
			#log.debug(f"Item {cache_key} is still valid")

		return expired


	def invalidate_page_if_expired(self, uuid: CustomUUID, last_update_time: str):
		cache_key = self.create_cache_key(str(uuid), ObjectType.PAGE)
		# FIXME: Some methods are checking timestamp internally, others are not

		# First check if the page exists at all
		with self.lock:
			self.cursor.execute('SELECT 1 FROM block_cache WHERE cache_key = ? AND object_type = ?', (cache_key, ObjectType.PAGE.value))
			exists = self.cursor.fetchone() is not None
		
		if not exists:
			# Page doesn't exist, count as a miss
			self._increment_metric('misses_not_found')
			return
			
		expired = self.check_if_expired(cache_key, ObjectType.PAGE, last_update_time)

		# Invalidate all blocks under this page
		if expired:
			# Page exists but is expired, count as a miss_expired
			self._increment_metric('misses_expired')
			self._invalidate_block_recursive(cache_key)
		
		# Use the internal method to directly invalidate the page itself
		# This should happen unconditionally when timestamp is newer than stored
		with self.lock:
			if self.check_if_expired(cache_key, ObjectType.PAGE, last_update_time):
				self.cursor.execute('DELETE FROM block_cache WHERE cache_key = ? AND object_type = ?', (cache_key, ObjectType.PAGE.value))
				self.cursor.execute('DELETE FROM block_relationships WHERE parent_key = ? OR child_key = ?', (cache_key, cache_key))
				self.remove_children_fetched_for_block(cache_key)
				self.conn.commit()
				self.set_dirty()
				log.debug(f"Invalidated page {cache_key} due to expiration")

		if expired:
			self._invalidate_parent_search_or_query(cache_key)


	def _get_block_internal(self, cache_key: str, object_type: ObjectType) -> Optional[str]:
		"""
		Returns the content of the block if it is not expired,
		otherwise deletes it and returns None
		"""

		with self.lock:
			self.cursor.execute('SELECT content, timestamp, ttl FROM block_cache WHERE cache_key = ? AND object_type = ?', (cache_key, object_type.value))
			result = self.cursor.fetchone()

			if result is not None:
				content, timestamp_str, ttl = result

				if ttl and ttl > 0:
					stored_time = datetime.strptime(timestamp_str, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)
					now = datetime.now(timezone.utc)
					if (now - stored_time).total_seconds() > ttl:
						log.debug(f"Item {cache_key} has expired")
						
						# Increment miss count for expired items
						self._increment_metric('misses_expired')

						self.cursor.execute('DELETE FROM block_cache WHERE cache_key = ? AND object_type = ?', (cache_key, object_type.value))
						self.conn.commit()
						self.set_dirty()
						return None

				# Increment hit count
				self._increment_metric('hits')
				#log.debug(f"Returning cached {cache_key}")
				return content
			else:
				# Increment miss count for not found items
				self._increment_metric('misses_not_found')
				return None


	def get_block(self, uuid: CustomUUID) -> Optional[str]:
		cache_key = self.create_cache_key(str(uuid), ObjectType.BLOCK)
		return self._get_block_internal(cache_key, ObjectType.BLOCK)


	def get_page(self, uuid: CustomUUID) -> Optional[str]:
		cache_key = self.create_cache_key(str(uuid), ObjectType.PAGE)
		return self._get_block_internal(cache_key, ObjectType.PAGE)


	def get_database(self, uuid: CustomUUID) -> Optional[str]:
		cache_key = self.create_cache_key(str(uuid), ObjectType.DATABASE)
		return self._get_block_internal(cache_key, ObjectType.DATABASE)


	def get_search_results(self, query: str, filter_str: Optional[str] = None, start_cursor: Optional[CustomUUID] = None) -> Optional[str]:
		cache_key = self.create_search_results_cache_key(query, filter_str, start_cursor)
		return self._get_block_internal(cache_key, ObjectType.SEARCH_RESULTS)


	def get_database_query_results(self, database_id: CustomUUID, filter_str: Optional[str] = None, start_cursor: Optional[CustomUUID] = None) -> Optional[str]:
		cache_key = self.create_database_query_results_cache_key(database_id, filter_str, start_cursor)
		return self._get_block_internal(cache_key, ObjectType.DATABASE_QUERY_RESULTS)


	def get_metrics(self) -> Dict[str, int]:
		"""
		Returns a dictionary with cache metrics.
		"""
		with self.lock:
			self.cursor.execute('SELECT metric_type, count FROM cache_metrics')
			results = self.cursor.fetchall()
			return {metric_type: count for metric_type, count in results}


	def verify_object_type_or_raise(self, uuid: CustomUUID, expected_type: ObjectType) -> None:
		"""
		Verify that the given UUID exists in cache with the expected object type.
		If the UUID exists with a different object type, raise ValueError.
		If the UUID doesn't exist at all, this method does nothing (no error).
		
		Args:
			uuid: The UUID to check
			expected_type: The expected ObjectType
			
		Raises:
			ValueError: If the UUID exists in cache but with a different object type
		"""
		cache_key = self.create_cache_key(str(uuid), expected_type)
		
		with self.lock:
			# Check if this UUID exists with any object type
			self.cursor.execute('SELECT object_type FROM block_cache WHERE cache_key = ?', (cache_key,))
			results = self.cursor.fetchall()
			
			if results:
				# Get all object types for this UUID
				existing_types = [result[0] for result in results]
				
				# If the expected type is not among the existing types, raise error

				if expected_type.value not in existing_types:
					existing_types_str = ", ".join(existing_types)
					raise ValueError(
						f"UUID {uuid} expected to be {expected_type.value} but it exists in cache with object type(s) [{existing_types_str}] "
					)


	def get_children_uuids(self, uuid: CustomUUID) -> List[CustomUUID]:
		cache_key = self.create_cache_key(str(uuid), ObjectType.BLOCK)

		children_keys = []
		with self.lock:
			self.cursor.execute('SELECT child_key FROM block_relationships WHERE parent_key = ?', (cache_key,))
			children_keys = self.cursor.fetchall()

		# Convert clean cache keys directly to CustomUUID objects
		return [CustomUUID.from_string(child_key_tuple[0]) for child_key_tuple in children_keys]


	def save(self):
		# Override abstract method

		# Check if we're in the process of closing or if connection is closed
		if self._is_closing or not self.conn:
			return

		try:
			with self.lock:
				# Double-check connection is still valid
				if not self.conn:
					return
					
				disk_conn = sqlite3.connect(self.db_path)
				with disk_conn:
					self.conn.backup(disk_conn)
				log.flow("Block cache saved to disk")
				self.clean()
		except sqlite3.Error as e:
			# Don't log errors if we're already closing
			if not self._is_closing:
				log.error(f"Failed to save block cache: {e}")


	def cleanup(self):
		#override

		#  TODO: This method is common, but only for db-based storage. Move to base class?

		# Don't do that during unit tests
		if not self.save_enabled:
			return

		# Prevent multiple cleanup calls
		if self._is_closing:
			return

		try:
			self._is_closing = True
			
			# Stop the periodic save thread first
			self.stop_periodic_save()
			
			# Save one final time if connection is still valid
			if self.conn:
				self.save()  # Call the virtual save method
				self.conn.close()
				self.conn = None
		except Exception as e:
			# Only log if it's not a "closed database" error during shutdown
			if "closed database" not in str(e).lower():
				log.error(f"Cleanup failed: {e}")


	def load_from_disk(self):
		try:
			with self.lock:
				disk_conn = sqlite3.connect(self.db_path)
				disk_conn.backup(self.conn)
				log.flow("Block cache loaded from disk")
				self.clean()
		except sqlite3.Error:
			log.flow("No existing block cache file found. Starting with an empty cache.")


	def get_blocks_updated_since(self, timestamp: str) -> List[Tuple[str, str, str, str]]:
		with self.lock:
			self.cursor.execute('''
				SELECT cache_key, object_type, content, timestamp
				FROM block_cache
				WHERE timestamp > ?
				ORDER BY timestamp DESC
			''', (timestamp,))
			return self.cursor.fetchall()


	def _invalidate_block_internal(self, cache_key: str, object_type: ObjectType, timestamp: str):
		
		# First check if the block exists
		with self.lock:
			self.cursor.execute('SELECT 1 FROM block_cache WHERE cache_key = ? AND object_type = ?', (cache_key, object_type.value))
			exists = self.cursor.fetchone() is not None
			
		if not exists:
			# Block doesn't exist, count as a miss
			self._increment_metric('misses_not_found')
			return
			
		if self.check_if_expired(cache_key, object_type, timestamp):
			# Block exists but is expired, count as a miss_expired
			self._increment_metric('misses_expired')
			
			with self.lock:
				self.cursor.execute('''
					DELETE FROM block_cache WHERE cache_key = ? AND object_type = ?
				''', (cache_key, object_type.value))
				self.conn.commit()
				self.set_dirty()
			log.debug(f"Invalidated item {cache_key} due to expiration")
		else:
			pass
			#log.debug(f"Item {cache_key} is still valid")


	def invalidate_database_if_expired(self, uuid: CustomUUID, timestamp: str):
		cache_key = self.create_cache_key(str(uuid), ObjectType.DATABASE)
		self._invalidate_block_internal(cache_key, ObjectType.DATABASE, timestamp)


	def remove_unused_blocks(self):
		
		# TODO: Trigger periodically?

		current_size = 0

		with self.lock:
			# Get current database size
			self.cursor.execute("PRAGMA page_count")
			page_count = self.cursor.fetchone()[0]
			self.cursor.execute("PRAGMA page_size")
			page_size = self.cursor.fetchone()[0]
			current_size = page_count * page_size

			if current_size <= self.max_size:
				return  # Database is already within size limit

			# Remove old blocks until the database fits the size limit
			while current_size > self.max_size:
				# Delete the oldest 1000 blocks
				self.cursor.execute('''
					DELETE FROM block_cache
					WHERE cache_key IN (
						SELECT cache_key FROM block_cache
						ORDER BY timestamp ASC
						LIMIT 1000
					)
				''')
				# TODO: Remove from other tables? What if block was not accessed but its parent was?

				self.conn.commit()
				self.set_dirty()

				# Recalculate the current size
				self.cursor.execute("PRAGMA page_count")
				page_count = self.cursor.fetchone()[0]
				current_size = page_count * page_size

				# Vacuum the database to reclaim space
				self.cursor.execute("VACUUM")
				self.conn.commit()
			


	def add_parent_child_relationship(self, parent_uuid: CustomUUID, child_uuid: CustomUUID, parent_type: ObjectType, child_type: ObjectType = ObjectType.BLOCK):

		parent_key = self.create_cache_key(str(parent_uuid), parent_type)
		child_key = self.create_cache_key(str(child_uuid), child_type)

		with self.lock:

			self.cursor.execute('''
				INSERT OR IGNORE INTO block_relationships (parent_key, child_key)
				VALUES (?, ?)
			''', (parent_key, child_key))
			
			self.conn.commit()
			self.set_dirty()

		#log.debug(f"Added parent-child relationship: {parent_key} -> {child_key}")


	def add_parent_children_relationships(self, parent_uuid: CustomUUID, children_uuids: List[CustomUUID], parent_type: ObjectType, child_type: ObjectType = ObjectType.BLOCK):
		parent_key = self.create_cache_key(str(parent_uuid), parent_type)
		with self.lock:
			child_keys = [(parent_key, self.create_cache_key(str(child_uuid), child_type)) for child_uuid in children_uuids]
			
			self.cursor.executemany('''
				INSERT OR IGNORE INTO block_relationships (parent_key, child_key)
				VALUES (?, ?)
			''', child_keys)
			
			self.conn.commit()
			self.set_dirty()

		log.debug(f"Added parent-children relationships: {parent_key} -> {len(children_uuids)} children")


	def add_children_fetched_for_block(self, cache_key: str):
		with self.lock:
			self.cursor.execute('''
				INSERT OR IGNORE INTO children_fetched_for_block (cache_key)
				VALUES (?)
			''', (cache_key,))
			self.conn.commit()
			self.set_dirty()


	def get_children_fetched_for_block(self, cache_key: str) -> bool:
		with self.lock:
			self.cursor.execute('SELECT 1 FROM children_fetched_for_block WHERE cache_key = ?', (cache_key,))
			return self.cursor.fetchone() is not None


	def remove_children_fetched_for_block(self, cache_key: str):
		with self.lock:
			self.cursor.execute('DELETE FROM children_fetched_for_block WHERE cache_key = ?', (cache_key,))
			self.conn.commit()
			self.set_dirty()
