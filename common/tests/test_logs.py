import unittest
from io import StringIO
import sys
from unittest.mock import patch

from tz_common.logs import log, LogLevel, LEVEL_COLORS

class TestLogs(unittest.TestCase):
	def test_log_levels(self):
		"""Test that log levels are properly defined."""
		self.assertEqual(LogLevel.FLOW, 5)
		self.assertEqual(LogLevel.DEBUG, 10)
		self.assertEqual(LogLevel.COMMON, 15)
		self.assertEqual(LogLevel.USER, 20)
		self.assertEqual(LogLevel.AI, 25)
		self.assertEqual(LogLevel.KNOWLEDGE, 30)
		self.assertEqual(LogLevel.ERROR, 35)
	
	def test_level_colors(self):
		"""Test that level colors are properly defined."""
		self.assertEqual(LEVEL_COLORS[LogLevel.FLOW], 'yellow')
		self.assertEqual(LEVEL_COLORS[LogLevel.DEBUG], 'magenta')
		self.assertEqual(LEVEL_COLORS[LogLevel.ERROR], 'red')
	
	@patch('sys.stdout', new_callable=StringIO)
	def test_log_output(self, mock_stdout):
		"""Test that log output works properly."""
		test_message = "test message"
		log.debug(test_message)
		self.assertIn(test_message, mock_stdout.getvalue())

if __name__ == '__main__':
	unittest.main() 