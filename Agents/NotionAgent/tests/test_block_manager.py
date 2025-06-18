import unittest
import sys
import os
import copy
import json
from unittest.mock import Mock, MagicMock

# Update the import path to include the project root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from operations.blocks.blockManager import BlockManager
from operations.blocks.blockHolder import BlockHolder, FilteringOptions
from operations.blocks.blockCache import BlockCache, ObjectType
from operations.blocks.index import Index
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


	def test_process_and_store_search_results_stores_and_returns_unfiltered(self):
		"""Test that search results are stored and returned unfiltered (filtering moved to agentTools)."""
		raw_results = self._create_search_results()
		
		# Process and store search results
		block_dict = self.block_manager.process_and_store_search_results("test query", raw_results)
		
		# Verify returned data is unfiltered (filtering now happens in agentTools)
		self.assertGreater(len(block_dict), 0)
		for block_id, block_content in block_dict.items():
			self.assertIn("type", block_content)  # Type should be preserved
			self.assertIn("last_edited_time", block_content)  # Timestamp should be preserved
			self.assertIn("icon", block_content)  # Icon should be preserved
		
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


	def test_process_children_response_returns_unfiltered_data(self):
		"""Test that process_children_response returns unfiltered data (filtering moved to agentTools)."""
		parent_uuid = CustomUUID.from_string(self.TEST_UUID_1)
		response_data = self._create_children_response()
		
		# Process children response (no filtering applied here anymore)
		block_dict = self.block_manager.process_children_response(
			response_data, parent_uuid, ObjectType.BLOCK
		)
		
		# Verify children are returned WITHOUT filtering applied
		self.assertGreater(len(block_dict), 0)
		for block_id, block_content in block_dict.items():
			# All fields should be preserved (unfiltered)
			self.assertIn("last_edited_time", block_content)  # Timestamp preserved
			self.assertIn("created_time", block_content)  # Timestamp preserved
			self.assertIn("icon", block_content)  # Icon preserved
			self.assertIn("bold", block_content)  # Style annotation preserved
			self.assertIn("type", block_content)  # Type preserved
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

	def test_caption_generation_queued_for_block_without_name(self):
		"""Test that caption generation is queued for blocks without names."""
		# Create a mock caption processor
		mock_caption_processor = Mock()
		
		# Create BlockManager with caption processor
		block_manager = BlockManager(
			self.index, self.cache, self.block_holder, 
			caption_processor=mock_caption_processor
		)
		
		raw_data = self._create_block_data()
		
		# Process and store the block (should queue caption generation)
		int_id = block_manager.process_and_store_block(raw_data, ObjectType.BLOCK)
		
		# Verify caption generation was queued
		mock_caption_processor.queue_caption_generation.assert_called_once()
		
		# Verify the call arguments
		call_args = mock_caption_processor.queue_caption_generation.call_args
		self.assertEqual(call_args.kwargs['int_id'], int_id)
		self.assertEqual(call_args.kwargs['block_type'], 'block')
		self.assertIsInstance(call_args.kwargs['uuid'], CustomUUID)
		self.assertIsInstance(call_args.kwargs['block_content'], dict)

	def test_caption_generation_not_queued_for_block_with_existing_name(self):
		"""Test that caption generation is not queued for blocks that already have names."""
		# Create a mock caption processor
		mock_caption_processor = Mock()
		
		# Create BlockManager with caption processor
		block_manager = BlockManager(
			self.index, self.cache, self.block_holder, 
			caption_processor=mock_caption_processor
		)
		
		raw_data = self._create_block_data()
		
		# First, add the UUID to index with a name
		uuid_obj = CustomUUID.from_string(self.TEST_UUID_1)
		int_id = self.index.add_uuid(uuid_obj, "Existing Block Name")
		
		# Process and store the block (should NOT queue caption generation)
		returned_int_id = block_manager.process_and_store_block(raw_data, ObjectType.BLOCK)
		
		# Verify the same int_id was returned
		self.assertEqual(int_id, returned_int_id)
		
		# Verify caption generation was NOT queued
		mock_caption_processor.queue_caption_generation.assert_not_called()

	def test_caption_generation_queued_for_block_with_whitespace_name(self):
		"""Test that caption generation is queued for blocks with whitespace-only names."""
		# Create a mock caption processor
		mock_caption_processor = Mock()
		
		# Create BlockManager with caption processor
		block_manager = BlockManager(
			self.index, self.cache, self.block_holder, 
			caption_processor=mock_caption_processor
		)
		
		raw_data = self._create_block_data()
		
		# First, add the UUID to index with whitespace-only name
		uuid_obj = CustomUUID.from_string(self.TEST_UUID_1)
		int_id = self.index.add_uuid(uuid_obj, "   ")  # Whitespace only
		
		# Process and store the block (should queue caption generation)
		returned_int_id = block_manager.process_and_store_block(raw_data, ObjectType.BLOCK)
		
		# Verify the same int_id was returned
		self.assertEqual(int_id, returned_int_id)
		
		# Verify caption generation was queued
		mock_caption_processor.queue_caption_generation.assert_called_once()

	def test_caption_generation_not_queued_when_processor_is_none(self):
		"""Test that no errors occur when caption processor is None."""
		# Create BlockManager without caption processor (None)
		block_manager = BlockManager(self.index, self.cache, self.block_holder, caption_processor=None)
		
		raw_data = self._create_block_data()
		
		# Process and store the block (should not raise any errors)
		int_id = block_manager.process_and_store_block(raw_data, ObjectType.BLOCK)
		
		# Verify the block was processed successfully
		self.assertIsInstance(int_id, int)
		
		# Verify the block was stored in cache
		uuid_obj = CustomUUID.from_string(self.TEST_UUID_1)
		cached_content = self.cache.get_block(uuid_obj)
		self.assertIsNotNone(cached_content)

	def test_caption_generation_conditional_logic_for_children(self):
		"""Test that conditional logic applies to children processed via process_children_batch."""
		# Create a mock caption processor
		mock_caption_processor = Mock()
		
		# Create BlockManager with caption processor
		block_manager = BlockManager(
			self.index, self.cache, self.block_holder, 
			caption_processor=mock_caption_processor
		)
		
		# Create parent and child data
		parent_uuid = CustomUUID.from_string(self.TEST_UUID_1)
		child_data = self._create_block_data(self.TEST_UUID_2)
		
		# Add child to index with existing name
		child_uuid = CustomUUID.from_string(self.TEST_UUID_2)
		self.index.add_uuid(child_uuid, "Existing Child Name")
		
		# Process children batch (should NOT queue caption for child with existing name)
		children_uuids = block_manager.process_children_batch([child_data], parent_uuid)
		
		# Verify child was processed
		self.assertEqual(len(children_uuids), 1)
		self.assertEqual(children_uuids[0], child_uuid)
		
		# Verify caption generation was NOT queued for child with existing name
		mock_caption_processor.queue_caption_generation.assert_not_called()


if __name__ == '__main__':
	unittest.main() 