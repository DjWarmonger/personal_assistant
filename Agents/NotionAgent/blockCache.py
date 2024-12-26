import sqlite3
import threading
import time
from typing import Optional, Tuple, List
from datetime import datetime, timezone
from enum import Enum
from abc import ABC, abstractmethod

from tz_common.logs import log
from tz_common.timed_storage import TimedStorage

class ObjectType(Enum):
	BLOCK = "block"
	PAGE = "page"
	DATABASE = "database"

class BlockCache(TimedStorage):

	def __init__(self, enable_disk_storage: bool = True):

		super().__init__(period_ms=5000, run_on_start=False)

		self.conn = sqlite3.connect(':memory:', check_same_thread=False)
		self.cursor = self.conn.cursor()
		self.lock = threading.Lock()
		self.dirty = False
		self.enable_disk_storage = enable_disk_storage

		self.load_from_disk()
		self.create_tables()

		# TODO: Set to low value for testing
		self.max_size = 64 * 1024 * 1024  # 64 MB in bytes

		self.start_periodic_save()


	@staticmethod
	def create_cache_key(uuid: str, object_type: ObjectType) -> str:
		return f"{object_type.value}:{uuid}"

	def create_tables(self):
		with self.lock:
			# Create block_cache table if it doesn't exist
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
			
			self.conn.commit()
			self.set_dirty()

	def _add_block_internal(self, cache_key: str, content: str, ttl: int = None, parent_key: str = None):
		now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
		
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
		
		log.debug(f'{"Updated" if exists else "Added"} block in cache: {cache_key}')

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

	def _invalidate_block_recursive(self, cache_key: str):

		child_keys = []
		with self.lock:
			
			# Find and recursively delete all child blocks
			self.cursor.execute('SELECT child_key FROM block_relationships WHERE parent_key = ?', (cache_key,))
			child_keys = self.cursor.fetchall()
			
			# Delete the current block
			self.cursor.execute('DELETE FROM block_cache WHERE cache_key = ?', (cache_key,))
			
			# Remove the relationships for this block
			self.cursor.execute('DELETE FROM block_relationships WHERE parent_key = ? OR child_key = ?', (cache_key, cache_key))
			
			self.conn.commit()
			self.set_dirty()

		for (child_key,) in child_keys:
			# FIXME: Never printed
			log.debug(f"Invalidating child {child_key}")
			self._invalidate_block_recursive(child_key)

	def invalidate_block_if_expired(self, uuid: str, timestamp: str):
		cache_key = self.create_cache_key(uuid, ObjectType.BLOCK)

		with self.lock:
			self.cursor.execute('SELECT timestamp FROM block_cache WHERE cache_key = ?', (cache_key,))
			result = self.cursor.fetchone()
			if result:
				if result[0] < timestamp:
					self._invalidate_block_recursive(cache_key)
					log.debug(f"Invalidated item {cache_key} and its children due to expiration")
				else:
					log.debug(f"Item {cache_key} is still valid")
			else:
				log.debug(f"Item {cache_key} not found in cache")

	def invalidate_page_if_expired(self, uuid: str, timestamp: str):
		cache_key = self.create_cache_key(uuid, ObjectType.PAGE)
		# Invalidate all blocks under this page
		self._invalidate_block_recursive(cache_key)
		
		# TODO: Check TTL (time to live for all but page info)
		self._invalidate_block_internal(cache_key, timestamp)

	def _get_block_internal(self, cache_key: str) -> Optional[str]:

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

						# TODO: Refactor but do not set double lock?
						self.cursor.execute('DELETE FROM block_cache WHERE cache_key = ?', (cache_key,))
						self.conn.commit()
						self.set_dirty()
						return None

				log.debug(f"Returning cached {cache_key.split(':')[1]}")
				return content
			else:
				return None
			
	def get_block(self, uuid: str) -> Optional[str]:
		cache_key = self.create_cache_key(uuid, ObjectType.BLOCK)
		return self._get_block_internal(cache_key)
			
	def get_page(self, uuid: str) -> Optional[str]:
		cache_key = self.create_cache_key(uuid, ObjectType.PAGE)
		return self._get_block_internal(cache_key)
	
	def get_database(self, uuid: str) -> Optional[str]:
		cache_key = self.create_cache_key(uuid, ObjectType.DATABASE)
		return self._get_block_internal(cache_key)
	

	def delete_block(self, cache_key: str) -> int:
		with self.lock:
			self.cursor.execute('DELETE FROM block_cache WHERE cache_key = ?', (cache_key,))
			self.conn.commit()
			self.set_dirty()
			return self.cursor.rowcount

	def save(self):
		# Override abstract method

		with self.lock:
			disk_conn = sqlite3.connect('block_cache.db')
			with disk_conn:
				self.conn.backup(disk_conn)
			log.flow("Block cache saved to disk")


	def load_from_disk(self):
		if not self.enable_disk_storage:
			return
		try:
			with self.lock:
				disk_conn = sqlite3.connect('block_cache.db')
				disk_conn.backup(self.conn)
				log.flow("Block cache loaded from disk")
				self.set_dirty(False)
		except sqlite3.Error:
			log.flow("No existing block cache file found. Starting with an empty cache.")

	def __del__(self):
		# TODO: Elegant way to force save?
		#self.save()
		self.conn.close()

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
		with self.lock:
			self.cursor.execute('''
				SELECT timestamp FROM block_cache WHERE cache_key = ?
				''', (cache_key,))
			result = self.cursor.fetchone()
			if result:
				stored_timestamp = result[0]
				if stored_timestamp and stored_timestamp < timestamp:
					self.cursor.execute('''
						DELETE FROM block_cache WHERE cache_key = ?
					''', (cache_key,))
					self.conn.commit()
					self.set_dirty()
					log.debug(f"Invalidated item {cache_key} due to expiration")
				else:
					log.debug(f"Item {cache_key} is still valid")
			else:
				log.debug(f"Item {cache_key} not found in cache")
		
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
				self.conn.commit()
				self.set_dirty()

				# Recalculate the current size
				self.cursor.execute("PRAGMA page_count")
				page_count = self.cursor.fetchone()[0]
				current_size = page_count * page_size

				# Vacuum the database to reclaim space
				self.cursor.execute("VACUUM")
				self.conn.commit()
			
			log.debug(f"Current size of block cache: {current_size / 1024 / 1024} MB")
			
	

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
