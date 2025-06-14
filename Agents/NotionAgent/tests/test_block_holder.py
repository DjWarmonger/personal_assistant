import unittest
import sys
import os
import copy

# Update the import path to include the project root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from operations.blocks.blockHolder import BlockHolder, FilteringOptions
from operations.blocks.index import Index
from operations.urlIndex import UrlIndex
from tz_common import CustomUUID


class TestBlockHolder(unittest.TestCase):

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
		"italic": False,
		"archived": False,
		"request_id": "req-123",
		"plain_text": "plain text"
	}
	
	# Error message template
	ERROR_MESSAGE_TEMPLATE = {
		"object": "error",
		"status": 404,
		"code": "object_not_found",
		"message": "Could not find object",
		"request_id": "req-123"
	}
	
	# Base message template
	BASE_MESSAGE_TEMPLATE = {
		"id": "test-id",
		**COMMON_FIELDS
	}

	def setUp(self):
		"""Set up test fixtures before each test method."""
		self.index = Index(load_from_disk=False, run_on_start=False)
		self.url_index = UrlIndex()
		self.block_holder = BlockHolder(self.url_index)

	def _create_error_message(self, **overrides):
		"""Helper method to create error message with optional overrides."""
		message = copy.deepcopy(self.ERROR_MESSAGE_TEMPLATE)
		message.update(overrides)
		return message

	def _create_base_message(self, **overrides):
		"""Helper method to create base message with optional overrides."""
		message = copy.deepcopy(self.BASE_MESSAGE_TEMPLATE)
		message.update(overrides)
		return message

	def _create_uuid_message(self, uuid_str=None, **overrides):
		"""Helper method to create message with UUID fields."""
		if uuid_str is None:
			uuid_str = self.TEST_UUID_1
		
		message = {
			"id": uuid_str,
			"page_id": uuid_str,
			"content": "test content",
			"short_id": "abc123"
		}
		message.update(overrides)
		return message

	def _create_nested_message(self, **overrides):
		"""Helper method to create message with nested structure."""
		message = self._create_base_message()
		message["nested"] = {
			"last_edited_time": self.TEST_TIMESTAMP,
			"text": "nested text",
			"strikethrough": True
		}
		message.update(overrides)
		return message

	def _create_metadata_message(self, **overrides):
		"""Helper method to create message with metadata fields."""
		message = self._create_base_message()
		message.update({
			"last_edited_by": {"id": "user-123"},
			"annotations": {"bold": True}
		})
		message.update(overrides)
		return message

	def _create_empty_values_message(self, **overrides):
		"""Helper method to create message with empty values."""
		message = self._create_base_message()
		message.update({
			"null_field": None,
			"empty_dict": {},
			"empty_list": [],
			"valid_dict": {"key": "value"},
			"valid_list": ["item"]
		})
		message.update(overrides)
		return message

	def _create_type_message(self, **overrides):
		"""Helper method to create message with type fields."""
		message = {
			"id": "test-id",
			"type": "block",
			"content": {
				"type": "paragraph",
				"text": "test text"
			}
		}
		message.update(overrides)
		return message

	def test_clean_error_message(self):
		message = self._create_error_message()
		
		result = self.block_holder.clean_error_message(message)
		
		# Should remove object and request_id
		self.assertNotIn("object", result)
		self.assertNotIn("request_id", result)
		
		# Should keep error details
		self.assertIn("status", result)
		self.assertIn("code", result)
		self.assertIn("message", result)

	def test_convert_uuids_to_int(self):
		uuid_obj = CustomUUID.from_string(self.TEST_UUID_1)
		message = self._create_uuid_message()
		
		uuid_to_int_map = {uuid_obj: 42}
		result = self.block_holder.convert_uuids_to_int(copy.deepcopy(message), uuid_to_int_map)
		
		# Should convert valid UUIDs to integers
		self.assertEqual(result["id"], 42)
		self.assertEqual(result["page_id"], 42)
		
		# Should keep non-UUID fields unchanged
		self.assertEqual(result["content"], "test content")
		self.assertEqual(result["short_id"], "abc123")

	def test_apply_timestamp_filters(self):
		message = self._create_nested_message()
		
		result = self.block_holder.apply_filters(copy.deepcopy(message), [FilteringOptions.TIMESTAMPS])
		
		# Should remove timestamp fields
		self.assertNotIn("last_edited_time", result)
		self.assertNotIn("created_time", result)
		self.assertNotIn("last_edited_time", result["nested"])
		
		# Should keep other fields
		self.assertIn("id", result)
		self.assertIn("content", result)
		self.assertIn("text", result["nested"])

	def test_apply_metadata_filters(self):
		message = self._create_metadata_message()
		message["nested"] = {"strikethrough": True, "text": "nested text"}
		
		result = self.block_holder.apply_filters(copy.deepcopy(message), [FilteringOptions.METADATA])
		
		# Should remove metadata fields
		self.assertNotIn("icon", result)
		self.assertNotIn("bold", result)
		self.assertNotIn("italic", result)
		self.assertNotIn("archived", result)
		self.assertNotIn("last_edited_by", result)
		self.assertNotIn("annotations", result)
		self.assertNotIn("plain_text", result)
		self.assertNotIn("strikethrough", result["nested"])
		
		# Should keep other fields
		self.assertIn("id", result)
		self.assertIn("content", result)
		self.assertIn("text", result["nested"])

	def test_apply_empty_values_filters(self):
		message = self._create_empty_values_message()
		
		result = self.block_holder.apply_filters(copy.deepcopy(message), [FilteringOptions.EMPTY_VALUES])
		
		# Should remove empty/null fields
		self.assertNotIn("null_field", result)
		self.assertNotIn("empty_dict", result)
		self.assertNotIn("empty_list", result)
		
		# Should keep non-empty fields
		self.assertIn("id", result)
		self.assertIn("content", result)
		self.assertIn("valid_dict", result)
		self.assertIn("valid_list", result)

	def test_apply_type_filters(self):
		message = self._create_type_message()
		
		result = self.block_holder.apply_filters(copy.deepcopy(message), [FilteringOptions.TYPE_FIELDS])
		
		# Should remove type fields
		self.assertNotIn("type", result)
		self.assertNotIn("type", result["content"])
		
		# Should keep other fields
		self.assertIn("id", result)
		self.assertIn("text", result["content"])

	def test_apply_system_fields_filters(self):
		message = self._create_base_message(other_field="keep this")
		
		result = self.block_holder.apply_filters(copy.deepcopy(message), [FilteringOptions.SYSTEM_FIELDS])
		
		# Should remove system fields
		self.assertNotIn("request_id", result)
		
		# Should keep other fields
		self.assertIn("id", result)
		self.assertIn("content", result)
		self.assertIn("other_field", result)

	def test_apply_minimal_filters(self):
		message = self._create_base_message()
		message.update({
			"type": "block",  # Should NOT be removed by MINIMAL
			"null_field": None  # Should be removed
		})
		
		result = self.block_holder.apply_filters(copy.deepcopy(message), [FilteringOptions.MINIMAL])
		
		# Should remove MINIMAL fields
		self.assertNotIn("last_edited_time", result)
		self.assertNotIn("icon", result)
		self.assertNotIn("null_field", result)
		
		# Should keep fields not in MINIMAL
		self.assertIn("id", result)
		self.assertIn("content", result)
		self.assertIn("type", result)  # Not removed by MINIMAL
		self.assertIn("request_id", result)  # Not removed by MINIMAL

	def test_apply_agent_optimized_filters(self):
		message = self._create_base_message()
		message.update({
			"type": "block",
			"null_field": None
		})
		
		result = self.block_holder.apply_filters(copy.deepcopy(message), [FilteringOptions.AGENT_OPTIMIZED])
		
		# Should remove all filterable fields
		self.assertNotIn("type", result)
		self.assertNotIn("last_edited_time", result)
		self.assertNotIn("icon", result)
		self.assertNotIn("null_field", result)
		self.assertNotIn("request_id", result)
		
		# Should keep essential fields
		self.assertIn("id", result)
		self.assertIn("content", result)

	def test_multiple_filter_options(self):
		message = self._create_base_message()
		message.update({
			"type": "block",
			"null_field": None
		})
		
		result = self.block_holder.apply_filters(
			copy.deepcopy(message), 
			[FilteringOptions.TIMESTAMPS, FilteringOptions.METADATA, FilteringOptions.EMPTY_VALUES]
		)
		
		# Should remove fields from all specified filters
		self.assertNotIn("last_edited_time", result)
		self.assertNotIn("icon", result)
		self.assertNotIn("null_field", result)
		
		# Should keep unfiltered fields
		self.assertIn("id", result)
		self.assertIn("content", result)
		self.assertIn("type", result)  # TYPE_FIELDS not specified


if __name__ == '__main__':
	unittest.main() 