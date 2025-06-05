import unittest
import sys
import os
import copy
import json

# Update the import path to include the project root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from operations.blockManager import BlockManager
from operations.blockHolder import BlockHolder, FilteringOptions
from operations.blockCache import BlockCache, ObjectType
from operations.index import Index
from operations.urlIndex import UrlIndex
from tz_common import CustomUUID


class TestBlockManager(unittest.TestCase):

	# Test data constants
	TEST_UUID_1 = "12345678-1234-1234-1234-123456789abc"
	TEST_UUID_2 = "87654321-4321-4321-4321-210987654321"
	TEST_TIMESTAMP = "2023-01-01T00:00:00Z"
	
	# Common field values
	COMMON_FIELDS = {
		"content": "test content",
		"last_edited_time": TEST_TIMESTAMP,
		"created_time": TEST_TIMESTAMP,
		"icon": "some-icon",
		"bold": True,
		"request_id": "req-123",
		"url": "https://example.com"
	}
	
	# Block data templates
	BLOCK_DATA_TEMPLATE = {
		"type": "block",
		"object": "block",
		**COMMON_FIELDS
	}
	
	PAGE_DATA_TEMPLATE = {
		"type": "page",
		"object": "page",
		"title": "Test Page",
		"last_edited_time": TEST_TIMESTAMP,
		"icon": "page-icon"
	}
	
	PARAGRAPH_BLOCK_TEMPLATE = {
		"type": "paragraph",
		"object": "block",
		"paragraph": {
			"rich_text": [{"type": "text", "text": {"content": "Child content"}}]
		},
		"last_edited_time": TEST_TIMESTAMP,
		"created_time": TEST_TIMESTAMP,
		"icon": "child-icon",
		"bold": True
	}

	def setUp(self):
		"""Set up test fixtures before each test method."""
		self.index = Index(load_from_disk=False, run_on_start=False)
		self.cache = BlockCache(load_from_disk=False, run_on_start=False)
		self.url_index = UrlIndex()
		self.block_holder = BlockHolder(self.url_index)
		self.block_manager = BlockManager(self.index, self.cache, self.block_holder)

	def _create_block_data(self, uuid_str=None, **overrides):
		"""Helper method to create block data with optional overrides."""
		if uuid_str is None:
			uuid_str = self.TEST_UUID_1
		
		data = {"id": uuid_str, **self.BLOCK_DATA_TEMPLATE}
		data.update(overrides)
		return data

	def _create_page_data(self, uuid_str=None, **overrides):
		"""Helper method to create page data with optional overrides."""
		if uuid_str is None:
			uuid_str = self.TEST_UUID_1
		
		data = {"id": uuid_str, **self.PAGE_DATA_TEMPLATE}
		data.update(overrides)
		return data

	def _create_search_results(self, uuid_str=None, **overrides):
		"""Helper method to create search results data."""
		if uuid_str is None:
			uuid_str = self.TEST_UUID_1
		
		result_data = {"id": uuid_str, **self.PAGE_DATA_TEMPLATE}
		result_data.update(overrides)
		
		return {
			"results": [result_data],
			"next_cursor": None,
			"has_more": False
		}

	def _create_children_response(self, child_uuid_str=None, **overrides):
		"""Helper method to create children response data."""
		if child_uuid_str is None:
			child_uuid_str = self.TEST_UUID_2
		
		child_data = {"id": child_uuid_str, **self.PARAGRAPH_BLOCK_TEMPLATE}
		child_data.update(overrides)
		
		return {"results": [child_data]}

	def test_process_and_store_block_stores_unfiltered_data(self):
		"""Test that process_and_store_block stores unfiltered data in cache."""
		raw_data = self._create_block_data()
		
		# Process and store the block
		int_id = self.block_manager.process_and_store_block(raw_data, ObjectType.BLOCK)
		
		# Verify the block was stored
		self.assertIsInstance(int_id, int)
		
		# Get the raw cached content
		uuid_obj = CustomUUID.from_string(self.TEST_UUID_1)
		cached_content = self.cache.get_block(uuid_obj)
		self.assertIsNotNone(cached_content)
		
		# Parse the cached content
		cached_data = self.block_manager.parse_cache_content(cached_content)
		
		# Verify unfiltered data is stored (should contain all original fields except UUIDs converted to ints)
		self.assertEqual(cached_data["id"], int_id)  # UUID converted to int
		self.assertEqual(cached_data["type"], "block")  # Type field preserved
		self.assertEqual(cached_data["content"], self.COMMON_FIELDS["content"])
		self.assertEqual(cached_data["last_edited_time"], self.TEST_TIMESTAMP)  # Timestamp preserved
		self.assertEqual(cached_data["created_time"], self.TEST_TIMESTAMP)  # Timestamp preserved
		self.assertEqual(cached_data["icon"], self.COMMON_FIELDS["icon"])  # Icon preserved
		self.assertEqual(cached_data["bold"], self.COMMON_FIELDS["bold"])  # Style annotation preserved
		self.assertEqual(cached_data["request_id"], self.COMMON_FIELDS["request_id"])  # System field preserved
		# URL should be preserved (not removed in unfiltered data)
		self.assertIn("url", cached_data)

	def test_get_filtered_block_content_applies_filtering(self):
		"""Test that get_filtered_block_content applies filtering correctly."""
		uuid_obj = CustomUUID.from_string(self.TEST_UUID_1)
		raw_data = self._create_block_data()
		
		# Store unfiltered data
		int_id = self.block_manager.process_and_store_block(raw_data, ObjectType.BLOCK)
		
		# Get filtered content with AGENT_OPTIMIZED filtering
		filtered_content = self.block_manager.get_filtered_block_content(
			uuid_obj, ObjectType.BLOCK, [FilteringOptions.AGENT_OPTIMIZED]
		)
		
		self.assertIsNotNone(filtered_content)
		
		# Verify filtering was applied
		self.assertEqual(filtered_content["id"], int_id)  # ID preserved
		self.assertEqual(filtered_content["content"], self.COMMON_FIELDS["content"])  # Content preserved
		self.assertNotIn("type", filtered_content)  # Type field removed
		self.assertNotIn("last_edited_time", filtered_content)  # Timestamp removed
		self.assertNotIn("icon", filtered_content)  # Icon removed
		self.assertNotIn("bold", filtered_content)  # Style annotation removed
		self.assertNotIn("request_id", filtered_content)  # System field removed

	def test_get_filtered_block_content_with_minimal_filtering(self):
		"""Test get_filtered_block_content with MINIMAL filtering."""
		uuid_obj = CustomUUID.from_string(self.TEST_UUID_1)
		raw_data = self._create_block_data()
		
		# Store unfiltered data
		int_id = self.block_manager.process_and_store_block(raw_data, ObjectType.BLOCK)
		
		# Get filtered content with MINIMAL filtering
		filtered_content = self.block_manager.get_filtered_block_content(
			uuid_obj, ObjectType.BLOCK, [FilteringOptions.MINIMAL]
		)
		
		self.assertIsNotNone(filtered_content)
		
		# Verify MINIMAL filtering was applied
		self.assertEqual(filtered_content["id"], int_id)  # ID preserved
		self.assertEqual(filtered_content["content"], self.COMMON_FIELDS["content"])  # Content preserved
		self.assertIn("type", filtered_content)  # Type field preserved (not in MINIMAL)
		self.assertNotIn("last_edited_time", filtered_content)  # Timestamp removed
		self.assertNotIn("icon", filtered_content)  # Icon removed
		self.assertIn("request_id", filtered_content)  # System field preserved (not in MINIMAL)

	def test_process_and_store_search_results_stores_unfiltered_returns_filtered(self):
		"""Test that search results are stored unfiltered but returned filtered."""
		raw_results = self._create_search_results()
		
		# Process and store search results
		block_dict = self.block_manager.process_and_store_search_results("test query", raw_results)
		
		# Verify returned data is filtered
		self.assertGreater(len(block_dict), 0)
		for block_id, block_content in block_dict.items():
			self.assertNotIn("type", block_content)  # Type should be filtered out
			self.assertNotIn("last_edited_time", block_content)  # Timestamp should be filtered out
			self.assertNotIn("icon", block_content)  # Icon should be filtered out
		
		# Verify unfiltered data is stored in cache
		cached_content = self.cache.get_search_results("test query")
		self.assertIsNotNone(cached_content)
		
		cached_data = self.block_manager.parse_cache_content(cached_content)
		first_result = cached_data["results"][0]
		
		# Cached data should contain all original fields (except UUID conversion)
		self.assertIsInstance(first_result["id"], int)  # UUID converted to int
		self.assertEqual(first_result["object"], "page")  # Object type preserved
		self.assertEqual(first_result["type"], "page")  # Type preserved in cache
		self.assertEqual(first_result["last_edited_time"], self.TEST_TIMESTAMP)  # Timestamp preserved
		self.assertEqual(first_result["title"], "Test Page")  # Title preserved
		self.assertEqual(first_result["icon"], "page-icon")  # Icon preserved in cache

	def test_process_children_response_applies_dynamic_filtering(self):
		"""Test that process_children_response applies dynamic filtering."""
		parent_uuid = CustomUUID.from_string(self.TEST_UUID_1)
		response_data = self._create_children_response()
		
		# Process children response with MINIMAL filtering
		block_dict = self.block_manager.process_children_response(
			response_data, parent_uuid, ObjectType.BLOCK, [FilteringOptions.MINIMAL]
		)
		
		# Verify children are returned with filtering applied
		self.assertGreater(len(block_dict), 0)
		for block_id, block_content in block_dict.items():
			# MINIMAL filtering should remove timestamps, icons, style annotations, empty values
			self.assertNotIn("last_edited_time", block_content)  # Timestamp removed
			self.assertNotIn("created_time", block_content)  # Timestamp removed
			self.assertNotIn("icon", block_content)  # Icon removed
			self.assertNotIn("bold", block_content)  # Style annotation removed
			# But should preserve type and object fields
			self.assertIn("type", block_content)  # Type preserved (not in MINIMAL)
			self.assertIn("object", block_content)  # Object preserved
		
		# Verify unfiltered data is stored in cache
		child_uuid = CustomUUID.from_string(self.TEST_UUID_2)
		cached_content = self.cache.get_block(child_uuid)
		self.assertIsNotNone(cached_content)
		
		cached_data = self.block_manager.parse_cache_content(cached_content)
		
		# Cached data should be unfiltered
		self.assertEqual(cached_data["type"], "paragraph")  # Type preserved
		self.assertEqual(cached_data["last_edited_time"], self.TEST_TIMESTAMP)  # Timestamp preserved
		self.assertEqual(cached_data["created_time"], self.TEST_TIMESTAMP)  # Timestamp preserved
		self.assertEqual(cached_data["icon"], "child-icon")  # Icon preserved
		self.assertEqual(cached_data["bold"], True)  # Style annotation preserved

	def test_legacy_vs_new_storage_difference(self):
		"""Test that new storage method stores more data than legacy method."""
		uuid_obj = CustomUUID.from_string(self.TEST_UUID_1)
		raw_data = self._create_block_data()
		
		# Test new method (stores unfiltered)
		int_id_new = self.block_manager.process_and_store_block(copy.deepcopy(raw_data), ObjectType.BLOCK)
		cached_new = self.cache.get_block(uuid_obj)
		cached_data_new = self.block_manager.parse_cache_content(cached_new)
		
		# Clear cache and test legacy method
		self.cache = BlockCache(load_from_disk=False, run_on_start=False)
		self.block_manager.cache = self.cache
		
		int_id_legacy = self.block_manager.process_and_store_block_legacy(copy.deepcopy(raw_data), ObjectType.BLOCK)
		cached_legacy = self.cache.get_block(uuid_obj)
		cached_data_legacy = self.block_manager.parse_cache_content(cached_legacy)
		
		# Both should have same int ID
		self.assertEqual(int_id_new, int_id_legacy)
		
		# New method should preserve more fields
		self.assertIn("type", cached_data_new)
		self.assertNotIn("type", cached_data_legacy)  # Legacy filters out type
		
		self.assertIn("last_edited_time", cached_data_new)
		self.assertNotIn("last_edited_time", cached_data_legacy)  # Legacy filters out timestamps
		
		self.assertIn("icon", cached_data_new)
		self.assertNotIn("icon", cached_data_legacy)  # Legacy filters out icons
		
		self.assertIn("request_id", cached_data_new)
		self.assertNotIn("request_id", cached_data_legacy)  # Legacy filters out system fields

	def test_get_filtered_block_content_nonexistent_block(self):
		"""Test get_filtered_block_content with non-existent block."""
		uuid_obj = CustomUUID.from_string(self.TEST_UUID_1)
		
		result = self.block_manager.get_filtered_block_content(uuid_obj, ObjectType.BLOCK)
		
		self.assertIsNone(result)

	def test_get_filtered_block_content_different_object_types(self):
		"""Test get_filtered_block_content with different object types."""
		page_uuid = CustomUUID.from_string(self.TEST_UUID_1)
		page_data = self._create_page_data()
		
		# Store as page
		self.block_manager.process_and_store_block(page_data, ObjectType.PAGE)
		
		# Retrieve with filtering
		filtered_content = self.block_manager.get_filtered_block_content(
			page_uuid, ObjectType.PAGE, [FilteringOptions.AGENT_OPTIMIZED]
		)
		
		self.assertIsNotNone(filtered_content)
		self.assertEqual(filtered_content["title"], "Test Page")
		self.assertNotIn("type", filtered_content)  # Filtered out
		self.assertNotIn("last_edited_time", filtered_content)  # Filtered out
		self.assertNotIn("icon", filtered_content)  # Filtered out


if __name__ == '__main__':
	unittest.main() 