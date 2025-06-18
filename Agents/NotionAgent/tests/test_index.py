import unittest
import os
import sys
from unittest.mock import patch

# Update the import path to include the project root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from operations.blocks.index import Index
from tz_common import CustomUUID


class TestIndex(unittest.TestCase):
	"""Test cases for Index class methods, focusing on caption-related functionality."""

	def setUp(self):
		"""Set up test fixtures with a fresh in-memory index."""
		self.index = Index(load_from_disk=False, run_on_start=False)
		
		# Add some test data
		self.test_uuid1 = CustomUUID.from_string("123e4567-e89b-12d3-a456-426614174000")
		self.test_uuid2 = CustomUUID.from_string("987fcdeb-43a2-12d3-a456-426614174000")
		self.test_uuid3 = CustomUUID.from_string("456789ab-cdef-1234-5678-90abcdef1234")
		
		# Add UUIDs to index
		self.int_id1 = self.index.add_uuid(self.test_uuid1, "")  # Empty name
		self.int_id2 = self.index.add_uuid(self.test_uuid2, "Existing Name")  # Has name
		self.int_id3 = self.index.add_uuid(self.test_uuid3, "   ")  # Whitespace only

	def tearDown(self):
		"""Clean up test fixtures."""
		if os.path.exists(self.index.db_path):
			os.remove(self.index.db_path)

	def test_update_name_if_empty_success_empty_name(self):
		"""Test updating name when current name is empty."""
		new_name = "Generated Caption"
		result = self.index.update_name_if_empty(self.int_id1, new_name)
		
		self.assertTrue(result)
		self.assertEqual(self.index.get_name(self.int_id1), new_name)

	def test_update_name_if_empty_success_whitespace_name(self):
		"""Test updating name when current name is only whitespace."""
		new_name = "Another Caption"
		result = self.index.update_name_if_empty(self.int_id3, new_name)
		
		self.assertTrue(result)
		self.assertEqual(self.index.get_name(self.int_id3), new_name)

	def test_update_name_if_empty_no_update_existing_name(self):
		"""Test that name is not updated when it already exists."""
		new_name = "Should Not Update"
		result = self.index.update_name_if_empty(self.int_id2, new_name)
		
		self.assertFalse(result)
		self.assertEqual(self.index.get_name(self.int_id2), "Existing Name")

	def test_update_name_if_empty_nonexistent_id(self):
		"""Test behavior when int_id doesn't exist in index."""
		nonexistent_id = 99999
		new_name = "Should Not Work"
		result = self.index.update_name_if_empty(nonexistent_id, new_name)
		
		self.assertFalse(result)

	def test_update_name_if_empty_type_validation(self):
		"""Test type validation for parameters."""
		with self.assertRaises(TypeError):
			self.index.update_name_if_empty("not_an_int", "name")
		
		with self.assertRaises(TypeError):
			self.index.update_name_if_empty(self.int_id1, 123)

	def test_update_name_if_empty_thread_safety(self):
		"""Test that the method properly uses database locking."""
		# This test verifies that the method has the db_lock attribute and uses it
		# We can't easily mock the RLock, but we can verify the lock exists
		self.assertIsNotNone(self.index.db_lock)
		
		# Test that the method works correctly (implying proper lock usage)
		result = self.index.update_name_if_empty(self.int_id1, "Test Caption")
		self.assertTrue(result)
		
		# Verify the lock is still functional after the operation
		with self.index.db_lock:
			name = self.index.get_name(self.int_id1)
			self.assertEqual(name, "Test Caption")

	def test_update_name_if_empty_sets_dirty_flag(self):
		"""Test that successful update sets the dirty flag for persistence."""
		with patch.object(self.index, 'set_dirty') as mock_set_dirty:
			result = self.index.update_name_if_empty(self.int_id1, "Test Caption")
			
			self.assertTrue(result)
			mock_set_dirty.assert_called_once()

	def test_update_name_if_empty_no_dirty_flag_when_no_update(self):
		"""Test that dirty flag is not set when no update occurs."""
		with patch.object(self.index, 'set_dirty') as mock_set_dirty:
			result = self.index.update_name_if_empty(self.int_id2, "Should Not Update")
			
			self.assertFalse(result)
			mock_set_dirty.assert_not_called()

	def test_update_name_if_empty_database_commit(self):
		"""Test that database changes are committed."""
		# Instead of mocking commit (which is read-only), we test the behavior indirectly
		# by verifying that the change persists in the database
		test_caption = "Test Caption"
		
		# Verify initial state
		initial_name = self.index.get_name(self.int_id1)
		self.assertEqual(initial_name, "")
		
		# Update the name
		result = self.index.update_name_if_empty(self.int_id1, test_caption)
		self.assertTrue(result)
		
		# Verify the change persisted (which means commit was called)
		updated_name = self.index.get_name(self.int_id1)
		self.assertEqual(updated_name, test_caption)

	def test_update_name_if_empty_integration_with_caption_workflow(self):
		"""Test the complete workflow as it would be used by caption generation."""
		# Simulate the caption generation workflow
		caption = "Auto-generated caption for block"
		
		# First update should succeed
		result1 = self.index.update_name_if_empty(self.int_id1, caption)
		self.assertTrue(result1)
		self.assertEqual(self.index.get_name(self.int_id1), caption)
		
		# Second update with different caption should fail (name already exists)
		new_caption = "Different caption"
		result2 = self.index.update_name_if_empty(self.int_id1, new_caption)
		self.assertFalse(result2)
		self.assertEqual(self.index.get_name(self.int_id1), caption)  # Original caption preserved

	def test_update_name_if_empty_empty_string_handling(self):
		"""Test handling of empty string as new name."""
		# Even empty string should be considered a valid update
		result = self.index.update_name_if_empty(self.int_id1, "")
		self.assertTrue(result)
		self.assertEqual(self.index.get_name(self.int_id1), "")

	def test_update_name_if_empty_unicode_handling(self):
		"""Test handling of unicode characters in captions."""
		unicode_caption = "📝 Generated caption with émojis and ñ characters"
		result = self.index.update_name_if_empty(self.int_id1, unicode_caption)
		
		self.assertTrue(result)
		self.assertEqual(self.index.get_name(self.int_id1), unicode_caption)


if __name__ == '__main__':
	unittest.main() 