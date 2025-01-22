import unittest
import time
import sys
import os
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from blockCache import BlockCache, ObjectType
from utils import Utils
class TestBlockCache(unittest.TestCase):
	def setUp(self):
		self.cache = BlockCache(load_from_disk=False, run_on_start=False)
		self.cache.max_size = 1024 * 1024  # Set a smaller max size for testing

	# TODO: Separate test for loading from disk and running on start

	def tearDown(self):
		del self.cache


	# TODO: Test if cached item is actually accessible
	def add_and_check_cached_block(self):

		content = "test_content"
		uuid = "test_uuid"

		self.cache.add_block(uuid, content)
		self.assertIsNotNone(self.cache.get_block(uuid))


	def check_formatted_uuid(self):
		uuid = "123e4567-e89b-12d3-a456-426614174000"
		content = "test_content"

		self.cache.add_block(uuid, content)

		self.assertIsNotNone(self.cache.get_block(uuid))
		self.assertIsNotNone(self.cache.get_block(uuid.lower()))
		self.assertIsNotNone(self.cache.get_block(uuid.upper()))
		short_formatted_uuid = self.cache.converter.to_formatted_uuid(uuid)
		self.assertIsNotNone(self.cache.get_block(short_formatted_uuid))

	# TODO: Test page

	def test_add_and_check_cached_search_results(self):
		# TODO; Also try pagination
		pass


	def test_add_and_check_cached_db_query_results(self):
		# TODO: Also try pagination
		pass


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


	def test_invalidate_page_if_expired(self):
		# Use the same timestamp format as _add_block_internal
		current_time = Utils.get_current_time_isoformat()
		
		self.cache.add_page("page_uuid", "page_content")
		self.assertIsNotNone(self.cache.get_page("page_uuid"))
		
		time.sleep(1)
		
		# Update time didn't change, so nothing should be invalidated
		self.cache.invalidate_page_if_expired("page_uuid", current_time)
		self.assertIsNotNone(self.cache.get_page("page_uuid"))

		# Get new time in same format
		new_time = Utils.get_current_time_isoformat()
		self.cache.invalidate_page_if_expired("page_uuid", new_time)
		self.assertIsNone(self.cache.get_page("page_uuid"))


	def test_invalidate_block_if_expired(self):

		# Use the same timestamp format as _add_block_internal
		current_time = Utils.get_current_time_isoformat()
		
		self.cache.add_block("block_uuid", "block_content")
		self.assertIsNotNone(self.cache.get_block("block_uuid"))
		
		time.sleep(1)
		
		# Update time didn't change, so nothing should be invalidated
		self.cache.invalidate_block_if_expired("block_uuid", current_time)
		self.assertIsNotNone(self.cache.get_block("block_uuid"))

		# Get new time in same format
		new_time = Utils.get_current_time_isoformat()
		self.cache.invalidate_block_if_expired("block_uuid", new_time)
		self.assertIsNone(self.cache.get_block("block_uuid"))


	def test_invalidating_parent_block(self):

		# TODO: When child block is nvalidated, it's parent page should not be invalidated
		# TODO: When a page is invaliudated, it's parent block should not be invalidated (page is not visible from block level)
		pass

if __name__ == '__main__':
	unittest.main()


