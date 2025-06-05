import unittest
import sys
import os
import copy

# Update the import path to include the project root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from operations.blockHolder import BlockHolder, FilteringOptions
from operations.index import Index
from operations.urlIndex import UrlIndex
from tz_common import CustomUUID


class TestBlockHolder(unittest.TestCase):

	def setUp(self):
		"""Set up test fixtures before each test method."""
		self.index = Index(load_from_disk=False, run_on_start=False)
		self.url_index = UrlIndex()
		self.block_holder = BlockHolder(self.url_index)


	def test_clean_error_message(self):
		"""Test cleaning of error messages."""
		message = {
			"object": "error",
			"status": 404,
			"code": "object_not_found",
			"message": "Could not find object",
			"request_id": "req-123"
		}
		
		result = self.block_holder.clean_error_message(message)
		
		# Should remove object and request_id
		self.assertNotIn("object", result)
		self.assertNotIn("request_id", result)
		
		# Should keep error details
		self.assertIn("status", result)
		self.assertIn("code", result)
		self.assertIn("message", result)


	# New tests for the filtering system
	def test_convert_uuids_to_int(self):
		"""Test the new UUID conversion method."""
		uuid_str = "12345678-1234-1234-1234-123456789abc"
		uuid_obj = CustomUUID.from_string(uuid_str)
		message = {
			"id": uuid_str,
			"page_id": uuid_str,
			"content": "test content",
			"short_id": "abc123"
		}
		
		uuid_to_int_map = {uuid_obj: 42}
		result = self.block_holder.convert_uuids_to_int(copy.deepcopy(message), uuid_to_int_map)
		
		# Should convert valid UUIDs to integers
		self.assertEqual(result["id"], 42)
		self.assertEqual(result["page_id"], 42)
		
		# Should keep non-UUID fields unchanged
		self.assertEqual(result["content"], "test content")
		self.assertEqual(result["short_id"], "abc123")


	def test_apply_timestamp_filters(self):
		"""Test timestamp filtering."""
		message = {
			"id": "test-id",
			"content": "test content",
			"last_edited_time": "2023-01-01T00:00:00Z",
			"created_time": "2023-01-01T00:00:00Z",
			"nested": {
				"last_edited_time": "2023-01-01T00:00:00Z",
				"text": "nested text"
			}
		}
		
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
		"""Test metadata filtering."""
		message = {
			"id": "test-id",
			"content": "test content",
			"icon": "some-icon",
			"bold": True,
			"italic": False,
			"archived": False,
			"last_edited_by": {"id": "user-123"},
			"annotations": {"bold": True},
			"plain_text": "plain text",
			"nested": {
				"strikethrough": True,
				"text": "nested text"
			}
		}
		
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
		"""Test empty values filtering."""
		message = {
			"id": "test-id",
			"content": "test content",
			"null_field": None,
			"empty_dict": {},
			"empty_list": [],
			"valid_dict": {"key": "value"},
			"valid_list": ["item"]
		}
		
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
		"""Test type field filtering."""
		message = {
			"id": "test-id",
			"type": "block",
			"content": {
				"type": "paragraph",
				"text": "test text"
			}
		}
		
		result = self.block_holder.apply_filters(copy.deepcopy(message), [FilteringOptions.TYPE_FIELDS])
		
		# Should remove type fields
		self.assertNotIn("type", result)
		self.assertNotIn("type", result["content"])
		
		# Should keep other fields
		self.assertIn("id", result)
		self.assertIn("text", result["content"])


	def test_apply_system_fields_filters(self):
		"""Test system fields filtering."""
		message = {
			"id": "test-id",
			"content": "test content",
			"request_id": "req-123",
			"other_field": "keep this"
		}
		
		result = self.block_holder.apply_filters(copy.deepcopy(message), [FilteringOptions.SYSTEM_FIELDS])
		
		# Should remove system fields
		self.assertNotIn("request_id", result)
		
		# Should keep other fields
		self.assertIn("id", result)
		self.assertIn("content", result)
		self.assertIn("other_field", result)


	def test_apply_minimal_filters(self):
		"""Test MINIMAL composite filter."""
		message = {
			"id": "test-id",
			"type": "block",  # Should NOT be removed by MINIMAL
			"content": "test content",
			"last_edited_time": "2023-01-01T00:00:00Z",  # Should be removed
			"icon": "some-icon",  # Should be removed
			"null_field": None,  # Should be removed
			"request_id": "req-123"  # Should NOT be removed by MINIMAL
		}
		
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
		"""Test AGENT_OPTIMIZED composite filter."""
		message = {
			"id": "test-id",
			"type": "block",
			"content": "test content",
			"last_edited_time": "2023-01-01T00:00:00Z",
			"icon": "some-icon",
			"null_field": None,
			"request_id": "req-123"
		}
		
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
		"""Test applying multiple individual filter options."""
		message = {
			"id": "test-id",
			"type": "block",
			"content": "test content",
			"last_edited_time": "2023-01-01T00:00:00Z",
			"icon": "some-icon",
			"null_field": None
		}
		
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