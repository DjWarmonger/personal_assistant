"""
Unit tests for modify operation.
"""
import pytest
from ..operations.modify import modify_json


def test_modify_basic():
	"""Test basic modify functionality."""
	json_doc = {
		"name": "John",
		"age": 30,
		"address": {
			"street": "123 Main St",
			"city": "New York"
		}
	}
	
	# Modify simple property
	result = modify_json(json_doc, "name", "Jane")
	assert result["name"] == "Jane"
	assert json_doc["name"] == "John"  # Original should not change
	
	# Modify nested property
	result = modify_json(json_doc, "address.city", "Boston")
	assert result["address"]["city"] == "Boston"
	assert json_doc["address"]["city"] == "New York"  # Original should not change


def test_modify_array():
	"""Test modify with arrays."""
	json_doc = {
		"users": [
			{"id": 1, "name": "Alice"},
			{"id": 2, "name": "Bob"},
			{"id": 3, "name": "Charlie"}
		]
	}
	
	# Modify array item
	result = modify_json(json_doc, "users.1", {"id": 2, "name": "Robert"})
	assert result["users"][1]["name"] == "Robert"
	assert json_doc["users"][1]["name"] == "Bob"  # Original should not change
	
	# Modify array item property
	result = modify_json(json_doc, "users.0.name", "Alicia")
	assert result["users"][0]["name"] == "Alicia"
	assert json_doc["users"][0]["name"] == "Alice"  # Original should not change


def test_modify_errors():
	"""Test error cases for modify operation."""
	json_doc = {
		"name": "John",
		"users": [
			{"id": 1, "name": "Alice"}
		]
	}
	
	# Path not found
	with pytest.raises(KeyError):
		modify_json(json_doc, "address.city", "Boston")
	
	# Invalid array index
	with pytest.raises(IndexError):
		modify_json(json_doc, "users.5", {})
	
	# Type error
	with pytest.raises(TypeError):
		modify_json(json_doc, "name.first", "John") 