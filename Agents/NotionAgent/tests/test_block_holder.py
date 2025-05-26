import unittest
import sys
import os

# Update the import path to include the project root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from operations.blockHolder import BlockHolder
from operations.index import Index
from operations.urlIndex import UrlIndex
from tz_common import CustomUUID


class TestBlockHolder(unittest.TestCase):

	def setUp(self):
		"""Set up test fixtures before each test method."""
		self.index = Index(load_from_disk=False, run_on_start=False)
		self.url_index = UrlIndex()
		self.block_holder = BlockHolder(self.index, self.url_index)


	def test_clean_response_details(self):
		"""Test cleaning of response details."""
		message = {
			"id": "test-id",
			"content": "test content",
			"icon": "some-icon",
			"bold": True,
			"request_id": "req-123",
			"nested": {
				"italic": False,
				"text": "nested text"
			}
		}
		
		result = self.block_holder.clean_response_details(message)
		
		# Should remove icon, bold, request_id, and nested italic
		self.assertNotIn("icon", result)
		self.assertNotIn("bold", result)
		self.assertNotIn("request_id", result)
		self.assertNotIn("italic", result["nested"])
		
		# Should keep id, content, and nested text
		self.assertIn("id", result)
		self.assertIn("content", result)
		self.assertIn("text", result["nested"])


	def test_clean_timestamps(self):
		"""Test removal of timestamp fields."""
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
		
		result = self.block_holder.clean_timestamps(message)
		
		# Should remove all timestamp fields
		self.assertNotIn("last_edited_time", result)
		self.assertNotIn("created_time", result)
		self.assertNotIn("last_edited_time", result["nested"])
		
		# Should keep other fields
		self.assertIn("id", result)
		self.assertIn("content", result)
		self.assertIn("text", result["nested"])


	def test_clean_type(self):
		"""Test removal of type fields."""
		message = {
			"id": "test-id",
			"type": "block",
			"content": {
				"type": "paragraph",
				"text": "test text"
			}
		}
		
		result = self.block_holder.clean_type(message)
		
		# Should remove all type fields
		self.assertNotIn("type", result)
		self.assertNotIn("type", result["content"])
		
		# Should keep other fields
		self.assertIn("id", result)
		self.assertIn("text", result["content"])


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


	def test_convert_to_index_id(self):
		"""Test conversion of UUIDs to index IDs."""
		uuid_str = "12345678-1234-1234-1234-123456789abc"
		message = {
			"id": uuid_str,
			"page_id": uuid_str,
			"content": "test content",
			"short_id": "abc123"  # Should not be converted
		}
		
		result = self.block_holder.convert_to_index_id(message)
		
		# Should convert valid UUIDs to integers
		self.assertIsInstance(result["id"], int)
		self.assertIsInstance(result["page_id"], int)
		
		# Should keep non-UUID fields unchanged
		self.assertEqual(result["content"], "test content")
		self.assertEqual(result["short_id"], "abc123")


	def test_convert_message_integration(self):
		"""Test the main convert_message method with all options."""
		uuid_str = "12345678-1234-1234-1234-123456789abc"
		message = {
			"id": uuid_str,
			"type": "block",
			"content": "test content",
			"last_edited_time": "2023-01-01T00:00:00Z",
			"icon": "some-icon",
			"request_id": "req-123"
		}
		
		result = self.block_holder.convert_message(message)
		
		# Should have converted UUID to int
		self.assertIsInstance(result["id"], int)
		
		# Should have removed cleaned fields
		self.assertNotIn("type", result)
		self.assertNotIn("last_edited_time", result)
		self.assertNotIn("icon", result)
		self.assertNotIn("request_id", result)
		
		# Should keep content
		self.assertIn("content", result)


if __name__ == '__main__':
	unittest.main() 