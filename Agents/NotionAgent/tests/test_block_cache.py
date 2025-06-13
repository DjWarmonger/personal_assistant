import time
import unittest

from tz_common import CustomUUID

from operations.blockCache import BlockCache, ObjectType
from operations.utils import Utils # Assuming Utils contains get_current_time_isoformat

# Predefined valid UUIDs for testing
TEST_UUID_1 = "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11"
TEST_UUID_2 = "0c7cb43c-09a6-45a8-9320-573189f0f8f4"
TEST_UUID_3 = "3d5b7a21-3056-4ea8-9dc0-301778710c55"
TEST_PAGE_UUID = "ef2f8a2c-12cc-473c-8b32-9f721070670c"
TEST_BLOCK_UUID = "abf39c9f-7cbf-4cea-8d83-1e05e417e047"
TEST_CHILD_BLOCK_UUID_1 = "fabdd1a3-cf08-49a5-819b-895819789359"
TEST_CHILD_BLOCK_UUID_2 = "acde070d-8c4c-4f0d-9d8a-162843c10333"
TEST_DATABASE_UUID = "12345678-1234-1234-1234-123456789abc"


class TestBlockCache(unittest.TestCase):

	def setUp(self):
		# Use an in-memory database for testing
		self.cache = BlockCache(db_path=':memory:', run_on_start=False)
		# Ensure tables are created for each test
		self.cache.create_tables()

	def tearDown(self):
		# Close the connection and clean up
		if hasattr(self.cache, '_is_closing'):
			self.cache._is_closing = True
		
		# Stop the periodic save thread first
		self.cache.stop_periodic_save()
		
		# Close the connection if it's still open
		if self.cache.conn:
			self.cache.conn.close()
			self.cache.conn = None
		# No need to delete a file if db_path is ':memory:'

	def test_add_and_get_block(self):
		self.cache.add_block(TEST_BLOCK_UUID, "test_content")
		retrieved_content = self.cache.get_block(TEST_BLOCK_UUID)
		self.assertEqual(retrieved_content, "test_content")

	def test_get_non_existent_block(self):
		retrieved_content = self.cache.get_block("a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a00") # Valid format, but non-existent
		self.assertIsNone(retrieved_content)

	def test_add_with_ttl(self):
		self.cache.add_block(TEST_UUID_1, "content_with_ttl", ttl=3600)
		retrieved_content = self.cache.get_block(TEST_UUID_1)
		self.assertEqual(retrieved_content, "content_with_ttl")

	def test_timed_expiration_deletion(self):
		# Add items with different expiration times
		self.cache.add_block(TEST_UUID_1, "content1", ttl=1)  # Expires in 1 second
		self.cache.add_block(TEST_UUID_2, "content2", ttl=3600) # Expires in 1 hour

		time.sleep(2) # Wait for the first item to expire

		self.assertIsNone(self.cache.get_block(TEST_UUID_1)) # Should be expired
		self.assertEqual(self.cache.get_block(TEST_UUID_2), "content2") # Should still exist

	def test_batch_deletion(self):
		# Add multiple items to the cache
		items = [(TEST_UUID_1, "content1"), (TEST_UUID_2, "content2"), (TEST_UUID_3, "content3")]
		for uuid_str, content in items:
				self.cache.add_block(uuid_str, content)

		# Ensure a different timestamp for invalidation check
		time.sleep(0.01) # Sleep for 10ms to ensure current time is later than stored time
		
		# Invalidate one block
		invalidated = self.cache.invalidate_block_if_expired(TEST_UUID_1, Utils.get_current_time_isoformat())
		self.assertTrue(invalidated, "Block should have been marked as expired and invalidated")
		self.assertIsNone(self.cache.get_block(TEST_UUID_1))
		
		# Check that other blocks are not affected (assuming no relationships that cause cascading deletion)
		self.assertIsNotNone(self.cache.get_block(TEST_UUID_2), "Block 2 should still exist")
		self.assertEqual(self.cache.get_block(TEST_UUID_2), "content2")
		self.assertIsNotNone(self.cache.get_block(TEST_UUID_3), "Block 3 should still exist")
		self.assertEqual(self.cache.get_block(TEST_UUID_3), "content3")


	def test_page_deletion_with_nested_children(self):
		# Add a page with nested children
		self.cache.add_page(TEST_PAGE_UUID, "page_content")
		self.cache.add_block(TEST_CHILD_BLOCK_UUID_1, "child_content_1", parent_uuid=TEST_PAGE_UUID, parent_type=ObjectType.PAGE)
		self.cache.add_block(TEST_CHILD_BLOCK_UUID_2, "child_content_2", parent_uuid=TEST_CHILD_BLOCK_UUID_1, parent_type=ObjectType.BLOCK)

		# Invalidate the page
		# To simulate expiration, pass a timestamp that is much later than when the page was added.
		future_timestamp = "2999-01-01T00:00:00.000Z" 
		self.cache.invalidate_page_if_expired(TEST_PAGE_UUID, future_timestamp)

		# Page and its children should be gone
		self.assertIsNone(self.cache.get_page(TEST_PAGE_UUID))
		self.assertIsNone(self.cache.get_block(TEST_CHILD_BLOCK_UUID_1))
		self.assertIsNone(self.cache.get_block(TEST_CHILD_BLOCK_UUID_2))

	def test_invalidate_page_if_expired(self):
		# Use the same timestamp format as _add_block_internal
		current_time = Utils.get_current_time_isoformat()

		self.cache.add_page(TEST_PAGE_UUID, "page_content")
		
		# Simulate time passing by creating a timestamp in the future
		# Making it a string as received from Notion API
		future_timestamp = "2999-01-01T00:00:00.000Z" 
		
		self.cache.invalidate_page_if_expired(TEST_PAGE_UUID, future_timestamp)
		self.assertIsNone(self.cache.get_page(TEST_PAGE_UUID))


	def test_invalidate_block_if_expired(self):

		# Use the same timestamp format as _add_block_internal
		current_time = Utils.get_current_time_isoformat()

		self.cache.add_block(TEST_BLOCK_UUID, "block_content")
		
		# Simulate time passing
		future_timestamp = "2999-01-01T00:00:00.000Z" 

		expired = self.cache.invalidate_block_if_expired(TEST_BLOCK_UUID, future_timestamp)
		self.assertTrue(expired)
		self.assertIsNone(self.cache.get_block(TEST_BLOCK_UUID))

	def test_get_children_uuids(self):
		parent_uuid = TEST_UUID_1
		child_uuid1 = TEST_UUID_2
		child_uuid2 = TEST_UUID_3

		self.cache.add_block(parent_uuid, "parent_content")
		self.cache.add_block(child_uuid1, "child1_content")
		self.cache.add_block(child_uuid2, "child2_content")

		self.cache.add_parent_children_relationships(parent_uuid, [child_uuid1, child_uuid2], ObjectType.BLOCK, ObjectType.BLOCK)

		children = self.cache.get_children_uuids(parent_uuid)
		self.assertEqual(len(children), 2)
		# get_children_uuids returns List[CustomUUID]
		children_str = [str(c) for c in children]
		self.assertIn(CustomUUID.from_string(child_uuid1).value, children_str)
		self.assertIn(CustomUUID.from_string(child_uuid2).value, children_str)

	def test_cache_metrics_hit(self):
		# Add a block to the cache
		self.cache.add_block(TEST_UUID_1, "test_content")
		
		# Get the block - should count as a hit
		content = self.cache.get_block(TEST_UUID_1)
		self.assertEqual(content, "test_content")
		
		# Check metrics
		metrics = self.cache.get_metrics()
		self.assertEqual(metrics["hits"], 1)
		
		# Get the block again - should count as another hit
		content = self.cache.get_block(TEST_UUID_1)
		
		# Check metrics again
		metrics = self.cache.get_metrics()
		self.assertEqual(metrics["hits"], 2)

	def test_cache_metrics_miss_not_found(self):
		# Try to get a non-existent block - should count as a miss
		non_existent_uuid = "b1eebc99-9c0b-4ef8-bb6d-6bb9bd380a22"
		content = self.cache.get_block(non_existent_uuid)
		self.assertIsNone(content)
		
		# Check metrics
		metrics = self.cache.get_metrics()
		self.assertEqual(metrics["misses_not_found"], 1)
		
		# Try invalidating a non-existent block - should also count as a miss
		self.cache.invalidate_block_if_expired(non_existent_uuid, Utils.get_current_time_isoformat())
		
		# Check metrics again
		metrics = self.cache.get_metrics()
		self.assertEqual(metrics["misses_not_found"], 2)

	def test_cache_metrics_miss_expired(self):
		# Add a block to the cache
		self.cache.add_block(TEST_UUID_1, "test_content", ttl=1)
		
		# Wait for the block to expire
		time.sleep(2)
		
		# Get the expired block - should count as a miss_expired
		content = self.cache.get_block(TEST_UUID_1)
		self.assertIsNone(content)
		
		# Check metrics
		metrics = self.cache.get_metrics()
		self.assertEqual(metrics["misses_expired"], 1)
		
		# Add another block and invalidate it explicitly
		self.cache.add_block(TEST_UUID_2, "test_content2")
		future_timestamp = "2999-01-01T00:00:00.000Z"
		self.cache.invalidate_block_if_expired(TEST_UUID_2, future_timestamp)
		
		# Check metrics again
		metrics = self.cache.get_metrics()
		self.assertEqual(metrics["misses_expired"], 2)
		
	def test_cache_metrics_integration(self):
		# Reset metrics by recreating tables
		self.cache.create_tables()
		
		# Add some blocks
		self.cache.add_block(TEST_UUID_1, "content1")
		self.cache.add_block(TEST_UUID_2, "content2", ttl=1)
		
		# Access existing block - should be a hit
		self.cache.get_block(TEST_UUID_1)
		
		# Wait for TTL to expire
		time.sleep(2)
		
		# Access expired block - should be a miss_expired
		self.cache.get_block(TEST_UUID_2)
		
		# Access non-existent block - should be a miss_not_found
		self.cache.get_block(TEST_UUID_3)
		
		# Invalidate an existing block - should be a miss_expired
		future_timestamp = "2999-01-01T00:00:00.000Z"
		self.cache.invalidate_block_if_expired(TEST_UUID_1, future_timestamp)
		
		# Check final metrics
		metrics = self.cache.get_metrics()
		self.assertEqual(metrics["hits"], 1)
		self.assertEqual(metrics["misses_expired"], 2)
		self.assertEqual(metrics["misses_not_found"], 1)

	def test_database_caching_with_object_type(self):
		"""Test that databases are cached with correct object type, separate from blocks"""
		
		# Add a database to cache
		test_content = {"object": "database", "title": "Test Database"}
		self.cache.add_database(TEST_DATABASE_UUID, test_content)
		
		# Verify cache key is clean (no prefix)
		cache_key = self.cache.create_cache_key(str(TEST_DATABASE_UUID), ObjectType.DATABASE)
		self.assertFalse(":" in cache_key, 
						f"Cache key should not contain prefixes, got: {cache_key}")
		
		# Verify we can retrieve it as a database
		retrieved_content = self.cache.get_database(TEST_DATABASE_UUID)
		self.assertIsNotNone(retrieved_content, "Database content should be retrievable")
		# Cache stores content as string representation
		self.assertEqual(retrieved_content, str(test_content))
		
		# Verify it's NOT cached as a block (this was the original bug)
		block_content = self.cache.get_block(TEST_DATABASE_UUID)
		self.assertIsNone(block_content, 
						  "Database should NOT be retrievable as a block")
		
		# Verify cache keys are the same for same UUID (since we removed prefixes)
		# but object types differentiate them in the database
		block_cache_key = self.cache.create_cache_key(str(TEST_DATABASE_UUID), ObjectType.BLOCK)
		database_cache_key = self.cache.create_cache_key(str(TEST_DATABASE_UUID), ObjectType.DATABASE)
		self.assertEqual(block_cache_key, database_cache_key,
						"Cache keys should be the same for same UUID (no prefixes)")
		
		# But they should be stored separately due to object_type column
		# Add the same UUID as a block
		self.cache.add_block(TEST_DATABASE_UUID, "block_content")
		
		# Both should be retrievable independently
		self.assertIsNotNone(self.cache.get_database(TEST_DATABASE_UUID))
		self.assertIsNotNone(self.cache.get_block(TEST_DATABASE_UUID))
		self.assertNotEqual(self.cache.get_database(TEST_DATABASE_UUID), 
						   self.cache.get_block(TEST_DATABASE_UUID))


	def test_database_invalidation_uses_correct_method(self):
		"""Test that database invalidation uses invalidate_database_if_expired, not invalidate_block_if_expired"""
		
		# Add a database to cache
		test_content = {"object": "database", "title": "Test Database"}
		self.cache.add_database(TEST_DATABASE_UUID, test_content)
		
		# Verify it exists
		self.assertIsNotNone(self.cache.get_database(TEST_DATABASE_UUID))
		
		# Invalidate using the correct database method
		future_timestamp = "2999-01-01T00:00:00.000Z"
		self.cache.invalidate_database_if_expired(TEST_DATABASE_UUID, future_timestamp)
		
		# Database should be gone
		self.assertIsNone(self.cache.get_database(TEST_DATABASE_UUID))
		
		# Add database again
		self.cache.add_database(TEST_DATABASE_UUID, test_content)
		self.assertIsNotNone(self.cache.get_database(TEST_DATABASE_UUID))
		
		# Try invalidating with block method - should NOT affect the database
		self.cache.invalidate_block_if_expired(TEST_DATABASE_UUID, future_timestamp)
		
		# Database should still exist because we used the wrong invalidation method
		self.assertIsNotNone(self.cache.get_database(TEST_DATABASE_UUID),
							 "Database should still exist when invalidated with block method")


	def test_verify_object_type_or_raise_no_conflict(self):
		"""Test that verify_object_type_or_raise doesn't raise when object type matches"""
		
		# Add a database to cache
		test_content = {"object": "database", "title": "Test Database"}
		self.cache.add_database(TEST_DATABASE_UUID, test_content)
		
		# Verify with correct type - should not raise
		try:
			self.cache.verify_object_type_or_raise(TEST_DATABASE_UUID, ObjectType.DATABASE)
		except ValueError:
			self.fail("verify_object_type_or_raise raised ValueError when it shouldn't have")


	def test_verify_object_type_or_raise_with_conflict(self):
		"""Test that verify_object_type_or_raise raises ValueError when object type conflicts"""
		
		# Add a database to cache
		test_content = {"object": "database", "title": "Test Database"}
		self.cache.add_database(TEST_DATABASE_UUID, test_content)
		
		# Verify with wrong type - should raise ValueError
		with self.assertRaises(ValueError) as context:
			self.cache.verify_object_type_or_raise(TEST_DATABASE_UUID, ObjectType.BLOCK)
		
		# Check error message contains useful information
		error_message = str(context.exception)
		self.assertIn("database", error_message)
		self.assertIn("block", error_message)
		self.assertIn(str(TEST_DATABASE_UUID), error_message)


	def test_verify_object_type_or_raise_nonexistent_uuid(self):
		"""Test that verify_object_type_or_raise doesn't raise for non-existent UUIDs"""
		
		# Try to verify a UUID that doesn't exist - should not raise
		non_existent_uuid = "00000000-0000-0000-0000-000000000000"
		try:
			self.cache.verify_object_type_or_raise(non_existent_uuid, ObjectType.DATABASE)
		except ValueError:
			self.fail("verify_object_type_or_raise raised ValueError for non-existent UUID")


	def test_verify_object_type_or_raise_multiple_types(self):
		"""Test verify_object_type_or_raise when same UUID exists with multiple object types"""
		
		# Add same UUID as both database and block
		self.cache.add_database(TEST_DATABASE_UUID, {"object": "database", "title": "Test Database"})
		self.cache.add_block(TEST_DATABASE_UUID, "block_content")
		
		# Verify with database type - should not raise
		try:
			self.cache.verify_object_type_or_raise(TEST_DATABASE_UUID, ObjectType.DATABASE)
		except ValueError:
			self.fail("verify_object_type_or_raise raised ValueError when database type exists")
		
		# Verify with block type - should not raise
		try:
			self.cache.verify_object_type_or_raise(TEST_DATABASE_UUID, ObjectType.BLOCK)
		except ValueError:
			self.fail("verify_object_type_or_raise raised ValueError when block type exists")
		
		# Verify with page type - should raise since page doesn't exist
		with self.assertRaises(ValueError) as context:
			self.cache.verify_object_type_or_raise(TEST_DATABASE_UUID, ObjectType.PAGE)
		
		error_message = str(context.exception)
		self.assertIn("database", error_message)
		self.assertIn("block", error_message)
		self.assertIn("page", error_message)


if __name__ == '__main__':
	unittest.main()


