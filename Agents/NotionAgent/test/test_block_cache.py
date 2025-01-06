import unittest
import time
import sys
import os
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from blockCache import BlockCache, ObjectType

class TestBlockCache(unittest.TestCase):
	def setUp(self):
		self.cache = BlockCache(load_from_disk=False, run_on_start=False)
		self.cache.max_size = 1024 * 1024  # Set a smaller max size for testing

	# TODO: Separate test for loading from disk and running on start

	def tearDown(self):
		del self.cache


	def test_basic_deletion(self):
		# Add an item to the cache
		self.cache.add_block("test_uuid", "test_content")
		
		# Verify the item is in the cache
		self.assertIsNotNone(self.cache.get_block("test_uuid"))
		
		# Delete the item
		self.cache.delete_block(self.cache.create_cache_key("test_uuid", ObjectType.BLOCK))
		
		# Verify the item is no longer in the cache
		self.assertIsNone(self.cache.get_block("test_uuid"))


	def test_deleting_non_existent_item(self):
		# Attempt to delete an item that doesn't exist in the cache
		result = self.cache.delete_block(self.cache.create_cache_key("non_existent_uuid", ObjectType.BLOCK))
		
		# Verify the operation doesn't cause errors and returns 0 (no rows affected)
		self.assertEqual(result, 0)


	def test_multiple_deletions(self):
		# Add multiple items to the cache
		items = [("uuid1", "content1"), ("uuid2", "content2"), ("uuid3", "content3")]
		for uuid, content in items:
			self.cache.add_block(uuid, content)
		
		# Delete all items one by one
		for uuid, _ in items:
			self.cache.delete_block(self.cache.create_cache_key(uuid, ObjectType.BLOCK))
		
		# Verify the cache is empty after all deletions
		for uuid, _ in items:
			self.assertIsNone(self.cache.get_block(uuid))


	def test_timed_expiration_deletion(self):
		# Add items with different expiration times
		self.cache.add_block("short_ttl", "content1", ttl=1)
		self.cache.add_block("long_ttl", "content2", ttl=10)
		
		# Wait for the short TTL item to expire
		time.sleep(2)
		
		# Verify expired item is automatically deleted while non-expired item remains
		self.assertIsNone(self.cache.get_block("short_ttl"))
		self.assertIsNotNone(self.cache.get_block("long_ttl"))


	def test_batch_deletion(self):
		# Add multiple items to the cache
		items = [("uuid1", "content1"), ("uuid2", "content2"), ("uuid3", "content3")]
		for uuid, content in items:
			self.cache.add_block(uuid, content)
		
		# Perform a batch delete operation
		with self.cache.lock:
			self.cache.cursor.executemany(
				'DELETE FROM block_cache WHERE cache_key = ?',
				[(self.cache.create_cache_key(uuid, ObjectType.BLOCK),) for uuid, _ in items]
			)
			self.cache.conn.commit()
		
		# Verify all specified items are removed at once
		for uuid, _ in items:
			self.assertIsNone(self.cache.get_block(uuid))


	def test_page_deletion_with_nested_children(self):
		# Add a page with nested children
		self.cache.add_page("page_uuid", "page_content")
		self.cache.add_block("child1_uuid", "child1_content", parent_uuid="page_uuid", parent_type=ObjectType.PAGE)
		self.cache.add_block("child2_uuid", "child2_content", parent_uuid="page_uuid", parent_type=ObjectType.PAGE)
		self.cache.add_block("grandchild_uuid", "grandchild_content", parent_uuid="child1_uuid", parent_type=ObjectType.BLOCK)
		
		# Invalidate the page
		self.cache.invalidate_page_if_expired("page_uuid", datetime.now(timezone.utc).isoformat())
		
		# Verify the page and all its children are removed
		self.assertIsNone(self.cache.get_page("page_uuid"))
		self.assertIsNone(self.cache.get_block("child1_uuid"))
		self.assertIsNone(self.cache.get_block("child2_uuid"))
		self.assertIsNone(self.cache.get_block("grandchild_uuid"))

if __name__ == '__main__':
	unittest.main()

