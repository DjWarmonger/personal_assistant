import sqlite3
import threading
import time
from typing import Optional, Tuple, List
from datetime import datetime, timezone
from enum import Enum
from abc import ABC, abstractmethod

from tz_common.logs import log
from tz_common.timed_storage import TimedStorage

from uuid_converter import UUIDConverter
from utils import Utils

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

		self.converter = UUIDConverter()

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


	def create_cache_key(self, uuid: str, object_type: ObjectType) -> str:
		return f"{object_type.value}:{self.converter.clean_uuid(uuid)}"


	def create_search_results_cache_key(self, query: str, filter : str = None, start_cursor: str = None) -> str:

		key  = query

		if filter is not None:
			key += f":{filter}"

		if start_cursor is not None:
			key += f":{self.converter.clean_uuid(start_cursor)}"

		return self.create_cache_key(key, ObjectType.SEARCH_RESULTS)


	def create_database_query_results_cache_key(self, database_id: str, filter : str = None, start_cursor: str = None) -> str:
		key  = self.converter.clean_uuid(database_id)

		if filter is not None:
			key += f":{filter}"

		if start_cursor is not None:
			key += f":{self.converter.clean_uuid(start_cursor)}"

		return self.create_cache_key(key, ObjectType.DATABASE_QUERY_RESULTS)


	def create_tables(self):
		with self.lock:
			# Create block_cache table if it doesn't exist

			# timestamp = last_edited_time

			self.cursor.execute('''
				CREATE TABLE IF NOT EXISTS block_cache (
					cache_key TEXT PRIMARY KEY,
					content TEXT,
					timestamp TEXT,
					ttl INTEGER
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
			
			self.conn.commit()
			self.set_dirty()


	def _add_block_internal(self, cache_key: str, content: str, ttl: int = None, parent_key: str = None):
		now = Utils.get_current_time_isoformat()

		content = str(content)
		
		with self.lock:
			# Check if the cache key already exists
			self.cursor.execute('SELECT 1 FROM block_cache WHERE cache_key = ?', (cache_key,))
			exists = self.cursor.fetchone() is not None
			
			self.cursor.execute('''
				INSERT OR REPLACE INTO block_cache (cache_key, content, timestamp, ttl)
				VALUES (?, ?, ?, ?)
			''', (cache_key, content, now, ttl))
			
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
				log.debug(f"Updating relationship: {parent_key} -> {cache_key}")
			else:
				log.debug(f"Adding relationship: {parent_key} -> {cache_key}")
		
		# FIXME: Do not print if content is identical?
		log.debug(f'{"Updated block in" if exists else "Added block to"} cache: {cache_key}')


	def add_block(self, uuid: str, content: str, ttl: int = None, parent_uuid: str = None, parent_type: ObjectType = ObjectType.BLOCK):

		cache_key = self.create_cache_key(uuid, ObjectType.BLOCK)

		parent_key = self.create_cache_key(parent_uuid, parent_type) if parent_uuid else None
		self._add_block_internal(cache_key, content, ttl, parent_key)


	def add_page(self, uuid: str, content: str, ttl: int = None):
		cache_key = self.create_cache_key(uuid, ObjectType.PAGE)
		self._add_block_internal(cache_key, content, ttl)


	def add_database(self, uuid: str, content: str, ttl: int = None):
		cache_key = self.create_cache_key(uuid, ObjectType.DATABASE)
		self._add_block_internal(cache_key, content, ttl)


	def add_search_results(self,
						query: str,
						content: str,
						filter : str = None,
						start_cursor: str = None,
						ttl: int = None):

		# TODO: Use ttl for search results?

		cache_key = self.create_search_results_cache_key(query, filter, start_cursor)
		self._add_block_internal(cache_key, content, ttl)


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


	def check_if_expired(self, cache_key: str, last_update_time: str) -> bool:

		with self.lock:
			self.cursor.execute('SELECT timestamp FROM block_cache WHERE cache_key = ?', (cache_key,))
			result = self.cursor.fetchone()
			if result:
				return result[0] < last_update_time
			else:
				log.debug(f"Item {cache_key} not found in cache")
				return False


	def invalidate_block_if_expired(self, uuid: str, last_update_time: str) -> bool:
		cache_key = self.create_cache_key(uuid, ObjectType.BLOCK)

		expired = self.check_if_expired(cache_key, last_update_time)

		if expired:
			self._invalidate_block_recursive(cache_key)
			log.debug(f"Invalidating item {cache_key} and its children due to expiration")
		else:
			pass
			#log.debug(f"Item {cache_key} is still valid")

		return expired


	def invalidate_page_if_expired(self, uuid: str, last_update_time: str):
		cache_key = self.create_cache_key(uuid, ObjectType.PAGE)
		# FIXME: Some methods are checking timestamp internally, others are not

		expired = self.check_if_expired(cache_key, last_update_time)

		# Invalidate all blocks under this page
		if expired:
			self._invalidate_block_recursive(cache_key)
		
		# TODO: Check TTL (time to live for all but page info)
		self._invalidate_block_internal(cache_key, last_update_time)

		if expired:
			self._invalidate_parent_search_or_query(cache_key)


	def _get_block_internal(self, cache_key: str) -> Optional[str]:
		"""
		Returns the content of the block if it is not expired,
		otherwise deletes it and returns None
		"""

		with self.lock:
			self.cursor.execute('SELECT content, timestamp, ttl FROM block_cache WHERE cache_key = ?', (cache_key,))
			result = self.cursor.fetchone()

			if result is not None:
				content, timestamp_str, ttl = result

				if ttl and ttl > 0:
					stored_time = datetime.strptime(timestamp_str, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)
					now = datetime.now(timezone.utc)
					if (now - stored_time).total_seconds() > ttl:
						log.debug(f"Item {cache_key} has expired")

						self.cursor.execute('DELETE FROM block_cache WHERE cache_key = ?', (cache_key,))
						self.conn.commit()
						self.set_dirty()
						return None

				#log.debug(f"Returning cached {cache_key.split(':')[1]}")
				return content
			else:
				return None


	def get_block(self, uuid: str) -> Optional[str]:
		uuid = self.converter.clean_uuid(uuid)
		cache_key = self.create_cache_key(uuid, ObjectType.BLOCK)
		return self._get_block_internal(cache_key)


	def get_page(self, uuid: str) -> Optional[str]:
		uuid = self.converter.clean_uuid(uuid)
		cache_key = self.create_cache_key(uuid, ObjectType.PAGE)
		return self._get_block_internal(cache_key)


	def get_database(self, uuid: str) -> Optional[str]:
		uuid = self.converter.clean_uuid(uuid)
		cache_key = self.create_cache_key(uuid, ObjectType.DATABASE)
		return self._get_block_internal(cache_key)


	def get_search_results(self, query: str, filter : str = None, start_cursor: str = None) -> Optional[str]:

		cache_key = self.create_search_results_cache_key(query, filter, start_cursor)
		return self._get_block_internal(cache_key)


	def get_database_query_results(self, database_id: str, filter : str = None, start_cursor: str = None) -> Optional[str]:
		database_id = self.converter.clean_uuid(database_id)
		cache_key = self.create_database_query_results_cache_key(database_id, filter, start_cursor)
		return self._get_block_internal(cache_key)


	def get_children_uuids(self, uuid: str) -> list[str]:

		cache_key = self.create_cache_key(uuid, ObjectType.BLOCK)

		#log.debug(f"Getting children indexes for {cache_key}")

		children_keys = []
		with self.lock:
			self.cursor.execute('SELECT child_key FROM block_relationships WHERE parent_key = ?', (cache_key,))
			children_keys = self.cursor.fetchall()

		return [self.converter.strip_cache_prefix(child_key) for (child_key,) in children_keys]


	def save(self):
		# Override abstract method

		with self.lock:
			disk_conn = sqlite3.connect(self.db_path)
			with disk_conn:
				self.conn.backup(disk_conn)
			log.flow("Block cache saved to disk")
			self.clean()


	def cleanup(self):
		#override

		#  TODO: This method is common, but only for db-based storage. Move to base class?

		# Don't do that during unit tests
		if not self.save_enabled:
			return

		if not self._is_closing and self.conn:
			try:
				self._is_closing = True
				self.save()  # Call the virtual save method
				self.conn.close()
			except Exception as e:
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


	def get_blocks_updated_since(self, timestamp: str) -> List[Tuple[str, str, str]]:
		with self.lock:
			self.cursor.execute('''
				SELECT uuid, content, timestamp
				FROM block_cache
				WHERE timestamp > ?
				ORDER BY timestamp DESC
			''', (timestamp,))
			return self.cursor.fetchall()


	def _invalidate_block_internal(self, cache_key: str, timestamp: str):
		
		if self.check_if_expired(cache_key, timestamp):
			self.cursor.execute('''
				DELETE FROM block_cache WHERE cache_key = ?
			''', (cache_key,))
			self.conn.commit()
			self.set_dirty()
			log.debug(f"Invalidated item {cache_key} due to expiration")
		else:
			pass
			#log.debug(f"Item {cache_key} is still valid")


	def invalidate_database_if_expired(self, uuid: str, timestamp: str):
		cache_key = self.create_cache_key(uuid, ObjectType.DATABASE)
		self._invalidate_block_internal(cache_key, timestamp)


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
			


	def add_parent_child_relationship(self, parent_uuid: str, child_uuid: str, parent_type: ObjectType, child_type: ObjectType = ObjectType.BLOCK):

		parent_key = self.create_cache_key(parent_uuid, parent_type)
		child_key = self.create_cache_key(child_uuid, child_type)

		with self.lock:

			self.cursor.execute('''
				INSERT OR IGNORE INTO block_relationships (parent_key, child_key)
				VALUES (?, ?)
			''', (parent_key, child_key))
			
			self.conn.commit()
			self.set_dirty()

		log.debug(f"Added parent-child relationship: {parent_key} -> {child_key}")


	def add_parent_children_relationships(self, parent_uuid: str, children_uuids: List[str], parent_type: ObjectType, child_type: ObjectType = ObjectType.BLOCK):
		parent_key = self.create_cache_key(parent_uuid, parent_type)
		with self.lock:
			child_keys = [(parent_key, self.create_cache_key(child_uuid, child_type)) for child_uuid in children_uuids]
			
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
