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


if __name__ == "__main__":
	unittest.main() 