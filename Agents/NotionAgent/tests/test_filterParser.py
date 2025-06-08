import pytest
import json
from unittest.mock import patch

from operations.utilities.filterParser import FilterParser


class TestFilterParser:
	"""Test suite for FilterParser utility class."""

	def test_parse_filter_none_input(self):
		"""Test parse_filter with None input returns empty dict."""
		result = FilterParser.parse_filter(None)
		assert result == {}

	def test_parse_filter_empty_dict_input(self):
		"""Test parse_filter with empty dict input."""
		result = FilterParser.parse_filter({})
		assert result == {}

	def test_parse_filter_dict_input(self):
		"""Test parse_filter with valid dict input."""
		filter_dict = {"property": "Status", "select": {"equals": "Done"}}
		result = FilterParser.parse_filter(filter_dict)
		assert result == filter_dict

	def test_parse_filter_valid_json_string(self):
		"""Test parse_filter with valid JSON string input."""
		filter_dict = {"property": "Status", "select": {"equals": "Done"}}
		filter_string = json.dumps(filter_dict)
		result = FilterParser.parse_filter(filter_string)
		assert result == filter_dict

	def test_parse_filter_invalid_json_string(self):
		"""Test parse_filter with invalid JSON string input."""
		invalid_json = '{"property": "Status", "select": {"equals": "Done"'  # Missing closing brace
		
		with patch('operations.utilities.filterParser.log') as mock_log:
			result = FilterParser.parse_filter(invalid_json)
			
		assert result == {}
		mock_log.error.assert_called_once()

	def test_parse_filter_empty_string(self):
		"""Test parse_filter with empty string input."""
		with patch('operations.utilities.filterParser.log') as mock_log:
			result = FilterParser.parse_filter("")
			
		assert result == {}
		mock_log.error.assert_called_once()

	def test_parse_filter_invalid_type(self):
		"""Test parse_filter with invalid type input."""
		with patch('operations.utilities.filterParser.log') as mock_log:
			result = FilterParser.parse_filter(123)  # Integer input
			
		assert result == {}
		mock_log.error.assert_called_once()

	def test_parse_filter_list_input(self):
		"""Test parse_filter with list input (invalid type)."""
		with patch('operations.utilities.filterParser.log') as mock_log:
			result = FilterParser.parse_filter([{"property": "Status"}])
			
		assert result == {}
		mock_log.error.assert_called_once()

	def test_parse_filter_complex_valid_dict(self):
		"""Test parse_filter with complex valid dictionary."""
		complex_filter = {
			"and": [
				{"property": "Status", "select": {"equals": "Done"}},
				{"property": "Priority", "select": {"equals": "High"}}
			]
		}
		result = FilterParser.parse_filter(complex_filter)
		assert result == complex_filter

	def test_parse_filter_complex_valid_json_string(self):
		"""Test parse_filter with complex valid JSON string."""
		complex_filter = {
			"or": [
				{"property": "Status", "select": {"equals": "In Progress"}},
				{"property": "Status", "select": {"equals": "Done"}}
			]
		}
		filter_string = json.dumps(complex_filter)
		result = FilterParser.parse_filter(filter_string)
		assert result == complex_filter

	def test_validate_database_filter_valid_dict(self):
		"""Test validate_database_filter with valid dictionary."""
		valid_filter = {"property": "Status", "select": {"equals": "Done"}}
		result = FilterParser.validate_database_filter(valid_filter)
		assert result is True

	def test_validate_database_filter_empty_dict(self):
		"""Test validate_database_filter with empty dictionary."""
		result = FilterParser.validate_database_filter({})
		assert result is True

	def test_validate_database_filter_invalid_type(self):
		"""Test validate_database_filter with invalid type."""
		result = FilterParser.validate_database_filter("not a dict")
		assert result is False

	def test_validate_database_filter_none(self):
		"""Test validate_database_filter with None."""
		result = FilterParser.validate_database_filter(None)
		assert result is False

	def test_validate_database_filter_complex_valid(self):
		"""Test validate_database_filter with complex valid filter."""
		complex_filter = {
			"and": [
				{"property": "Status", "select": {"equals": "Done"}},
				{"property": "Created", "date": {"past_week": {}}}
			]
		}
		result = FilterParser.validate_database_filter(complex_filter)
		assert result is True

	def test_validate_database_filter_non_serializable(self):
		"""Test validate_database_filter with non-JSON-serializable content."""
		# Create a dict with non-serializable content
		invalid_filter = {"property": "Status", "function": lambda x: x}
		result = FilterParser.validate_database_filter(invalid_filter)
		assert result is False

	def test_parse_filter_preserves_original_dict(self):
		"""Test that parse_filter doesn't modify the original dictionary."""
		original_filter = {"property": "Status", "select": {"equals": "Done"}}
		original_copy = original_filter.copy()
		
		result = FilterParser.parse_filter(original_filter)
		
		# Original should be unchanged
		assert original_filter == original_copy
		# Result should be equal but potentially different object
		assert result == original_filter 