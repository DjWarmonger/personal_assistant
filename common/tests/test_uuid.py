import unittest
import re
from tz_common import CustomUUID
from tz_common.uuid import UUID_PATTERN, NORMALIZED_UUID_PATTERN


class TestCustomUUID(unittest.TestCase):
	
	def test_creation_and_formatting(self):
		# Test creating a UUID from formatted string
		formatted_uuid = "1029efeb-6676-8044-88d6-c61da2eb04b9"
		normalized = formatted_uuid.replace("-", "").lower()
		
		uuid1 = CustomUUID(value=formatted_uuid)
		self.assertEqual(str(uuid1), normalized)
		
		# Test creating from already normalized string
		uuid2 = CustomUUID(value=normalized)
		self.assertEqual(str(uuid2), normalized)
		
		# Test formatting back to standard format
		self.assertEqual(uuid1.to_formatted(), formatted_uuid)
		
		# Test creating from non-standard format string
		uuid3 = CustomUUID(value="1029EFEB-6676-8044-88D6-C61DA2EB04B9")  # Uppercase
		self.assertEqual(str(uuid3), normalized)
		self.assertEqual(uuid1, uuid3)
	
	def test_from_string(self):
		# Reference UUID in normalized form (without hyphens)
		formatted_uuid = "1029efeb-6676-8044-88d6-c61da2eb04b9"
		normalized = formatted_uuid.replace("-", "").lower()
		
		# Test with various formats
		test_cases = [
			"1029efeb-6676-8044-88d6-c61da2eb04b9",  # Standard format with hyphens
			"1029efeb6676804488d6c61da2eb04b9",      # Continuous form
			"1029EFEB-6676-8044-88D6-C61DA2EB04B9",  # Uppercase with hyphens
			"1029EFEB6676804488D6C61DA2EB04B9"       # Uppercase continuous
		]
		
		for test_case in test_cases:
			uuid = CustomUUID.from_string(test_case)
			self.assertEqual(str(uuid), normalized)
			self.assertIsInstance(uuid, CustomUUID)
		
		# Test invalid cases
		invalid_cases = [
			"",                                      # Empty string
			"invalid-uuid",                          # Not a UUID
			"1029efeb-6676-8044-88d6-c61da2eb04",    # Too short
			"1029efeb-6676-8044-88d6-c61da2eb04b9a"  # Too long
		]
		
		for invalid_case in invalid_cases:
			with self.assertRaises(ValueError):
				CustomUUID.from_string(invalid_case)
	
	def test_uuid1_generation(self):
		# Test generating a new UUID1
		new_uuid = CustomUUID.uuid1()
		self.assertIsNotNone(new_uuid)
		
		# Should be in normalized form
		self.assertEqual(len(str(new_uuid)), 32)
		self.assertFalse("-" in str(new_uuid))
		
		# Formatted version should have hyphens
		formatted = new_uuid.to_formatted()
		self.assertEqual(len(formatted), 36)
		self.assertTrue(UUID_PATTERN.match(formatted))
	
	def test_validation(self):
		# Test validation on creation
		with self.assertRaises(ValueError):
			CustomUUID(value="invalid-uuid")
		
		# Test validation method with different formats
		self.assertTrue(CustomUUID.validate("1029efeb-6676-8044-88d6-c61da2eb04b9"))  # With hyphens (standard)
		self.assertTrue(CustomUUID.validate("1029efeb6676804488d6c61da2eb04b9"))      # Without hyphens (normalized)
		self.assertTrue(CustomUUID.validate("1029EFEB-6676-8044-88D6-C61DA2EB04B9"))  # Uppercase
		
		# Test non-standard formats (these should now pass validation)
		non_standard = "1029efeb6676-8044-88d6-c61da2eb04b9"  # Non-standard hyphen placement
		self.assertTrue(CustomUUID.validate(non_standard))
		
		# Test invalid values
		self.assertFalse(CustomUUID.validate("invalid-uuid"))
		self.assertFalse(CustomUUID.validate("1029efeb-6676-8044-88d6-c61d"))  # Too short
		self.assertFalse(CustomUUID.validate("1029efeb-6676-8044-88d6-c61da2eb04b9a"))  # Too long
		self.assertFalse(CustomUUID.validate(None))
		self.assertFalse(CustomUUID.validate(123))
	
	def test_equality(self):
		# Test equality operator with standard format
		uuid1 = CustomUUID.from_string("1029efeb-6676-8044-88d6-c61da2eb04b9")
		# With normalized format (no hyphens)
		uuid2 = CustomUUID.from_string("1029efeb6676804488d6c61da2eb04b9")
		# Different UUID
		uuid3 = CustomUUID.from_string("2039efeb-6676-8044-88d6-c61da2eb04b9")
		
		# UUIDs with the same value should be equal
		self.assertEqual(uuid1, uuid2)
		self.assertNotEqual(uuid1, uuid3)
		
		# Test equality with string
		self.assertEqual(uuid1, "1029efeb-6676-8044-88d6-c61da2eb04b9")  # With hyphens
		self.assertEqual(uuid1, "1029efeb6676804488d6c61da2eb04b9")      # Without hyphens
		self.assertNotEqual(uuid1, "invalid-uuid")
	
	def test_hash(self):
		# Test using UUIDs as dictionary keys
		uuid1 = CustomUUID.from_string("1029efeb-6676-8044-88d6-c61da2eb04b9")
		uuid2 = CustomUUID.from_string("1029efeb6676804488d6c61da2eb04b9")  # Same UUID without hyphens
		
		uuid_dict = {uuid1: "value1", uuid2: "value2"}
		# Should be considered the same key
		self.assertEqual(len(uuid_dict), 1)
		self.assertEqual(uuid_dict[uuid1], "value2")  # Last assigned value wins
	
	def test_conversion(self):
		# Test conversion to Python UUID
		uuid1 = CustomUUID.from_string("1029efeb-6676-8044-88d6-c61da2eb04b9")
		py_uuid = uuid1.to_python_uuid()
		
		# Python UUID's string representation has hyphens
		self.assertEqual(str(py_uuid), "1029efeb-6676-8044-88d6-c61da2eb04b9")
		# But when normalized, they should match
		self.assertEqual(str(py_uuid).replace("-", "").lower(), str(uuid1))


class TestUUIDMigration(unittest.TestCase):
	
	def test_migration_compatibility(self):
		"""Test that the new CustomUUID is compatible with the old string-based approach"""
		original_uuid = "1029efeb-6676-8044-88d6-c61da2eb04b9"
		
		# Old approach (using raw strings)
		old_clean = original_uuid.replace("-", "").lower()
		old_formatted = f"{old_clean[:8]}-{old_clean[8:12]}-{old_clean[12:16]}-{old_clean[16:20]}-{old_clean[20:]}"
		
		# New approach
		new_uuid = CustomUUID.from_string(original_uuid)
		new_clean = str(new_uuid)
		new_formatted = new_uuid.to_formatted()
		
		# Verify compatibility
		self.assertEqual(old_clean, new_clean)
		self.assertEqual(old_formatted, new_formatted)


if __name__ == "__main__":
	unittest.main() 