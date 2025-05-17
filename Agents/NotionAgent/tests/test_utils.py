import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tz_common import CustomUUID
from operations.utils import Utils


class TestUtils(unittest.TestCase):
	
	def test_current_time_isoformat(self):
		# Test that the method returns a string in the expected format
		time_str = Utils.get_current_time_isoformat()
		self.assertIsInstance(time_str, str)
		self.assertEqual(len(time_str), 24)  # Format: "2023-04-26T12:34:56.789Z"
		self.assertTrue(time_str.endswith("Z"))
	
	def test_strip_cache_prefix(self):
		# Test with valid prefixed UUID
		test_uuid = "1029efeb-6676-8044-88d6-c61da2eb04b9"
		normalized = test_uuid.replace("-", "").lower()
		
		# Test with different prefix formats
		prefixed_uuid = f"page:{test_uuid}"
		result = Utils.strip_cache_prefix(prefixed_uuid)
		
		# Check that result is a CustomUUID
		self.assertIsInstance(result, CustomUUID)
		
		# Check that UUID value is normalized (no hyphens, lowercase)
		self.assertEqual(str(result), normalized)
		
		# Test with block prefix
		block_prefixed = f"block:{test_uuid}"
		block_result = Utils.strip_cache_prefix(block_prefixed)
		self.assertEqual(str(block_result), normalized)
		
		# Test with database prefix
		db_prefixed = f"database:{test_uuid}"
		db_result = Utils.strip_cache_prefix(db_prefixed)
		self.assertEqual(str(db_result), normalized)
		
		# Test with already normalized UUID
		norm_prefixed = f"page:{normalized}"
		norm_result = Utils.strip_cache_prefix(norm_prefixed)
		self.assertEqual(str(norm_result), normalized)
		
		# Test that different prefixes with the same UUID result in equal UUIDs
		self.assertEqual(result, block_result)
		self.assertEqual(result, db_result)
		self.assertEqual(result, norm_result)
		
		# Test with invalid input (no prefix)
		with self.assertRaises(ValueError):
			Utils.strip_cache_prefix(test_uuid)


if __name__ == "__main__":
	unittest.main() 