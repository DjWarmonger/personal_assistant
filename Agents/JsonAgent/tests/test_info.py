"""
Unit tests for info operation.
"""
import pytest
from ..operations.info import get_json_info


def test_info_basic():
	"""Test basic info functionality."""
	json_doc = {
		"name": "John",
		"age": 30,
		"address": {
			"street": "123 Main St",
			"city": "New York"
		},
		"hobbies": ["reading", "gaming"],
		"empty_obj": {},
		"empty_arr": []
	}
	
	# Test object info
	result = get_json_info(json_doc, "address")
	assert result == "Object with keys: ['street', 'city']"
	
	# Test array info
	result = get_json_info(json_doc, "hobbies")
	assert result == "Array with size: 2"
	
	# Test empty object
	result = get_json_info(json_doc, "empty_obj")
	assert result == "Object: EMPTY"
	
	# Test empty array
	result = get_json_info(json_doc, "empty_arr")
	assert result == "Array: EMPTY"


def test_info_nested():
	"""Test info functionality with nested paths."""
	json_doc = {
		"users": [
			{
				"id": 1,
				"settings": {
					"theme": "dark",
					"notifications": True
				},
				"posts": []
			}
		]
	}
	
	# Test nested object
	result = get_json_info(json_doc, "users.0.settings")
	assert result == "Object with keys: ['theme', 'notifications']"
	
	# Test nested empty array
	result = get_json_info(json_doc, "users.0.posts")
	assert result == "Array: EMPTY"


def test_info_errors():
	"""Test error cases."""
	json_doc = {
		"users": [
			{"name": "John"}
		],
		"settings": {
			"theme": "dark"
		}
	}
	
	# Test invalid path
	with pytest.raises(KeyError):
		get_json_info(json_doc, "invalid.path")
	
	# Test invalid array index
	with pytest.raises(IndexError):
		get_json_info(json_doc, "users.1")
	
	# Test primitive value - should return a string description, not raise an error
	result = get_json_info(json_doc, "settings.theme")
	assert "Primitive value" in result 