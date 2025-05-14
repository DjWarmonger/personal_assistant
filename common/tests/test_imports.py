import unittest
import importlib.util

class TestImports(unittest.TestCase):
	def test_basic_imports(self):
		"""Test basic imports from tz_common package."""
		from tz_common.logs import log, LogLevel
		from tz_common.utils import TZUtils
		
		# Check log class has proper methods
		self.assertTrue(hasattr(log, 'user'))
		self.assertTrue(hasattr(log, 'debug'))
		self.assertTrue(hasattr(log, 'error'))
		
		# Check LogLevel enum
		self.assertTrue(hasattr(LogLevel, 'DEBUG'))
		self.assertTrue(hasattr(LogLevel, 'ERROR'))
		
		# Check TZUtils class has methods
		self.assertTrue(hasattr(TZUtils, 'resize_image'))
		self.assertTrue(hasattr(TZUtils, 'load_images'))
	
	def test_tzrag_exists(self):
		"""Test that tzrag module exists, regardless of its dependencies."""
		import os.path
		# Check if the file exists in the package
		tzrag_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'src', 'tz_common', 'tzrag.py')
		self.assertTrue(os.path.exists(tzrag_path), "tzrag.py file should exist")

if __name__ == '__main__':
	unittest.main() 