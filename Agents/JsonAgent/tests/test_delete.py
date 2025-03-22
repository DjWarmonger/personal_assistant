"""
Unit tests for delete operation.
"""
import pytest
from ..operations.delete import delete_from_json


def test_delete_basic():
	"""Test basic delete functionality."""
	json_doc = {
		"name": "John",
		"age": 30,
		"address": {
			"street": "123 Main St",
			"city": "New York"
		}
	}
	
	# Delete simple property
	result = delete_from_json(json_doc, "age")
	assert "age" not in result
	assert "age" in json_doc  # Original should not change
	
	# Delete nested property
	result = delete_from_json(json_doc, "address.city")
	assert "city" not in result["address"]
	assert "city" in json_doc["address"]  # Original should not change


def test_delete_from_array():
	"""Test delete with arrays."""
	json_doc = {
		"users": [
			{"id": 1, "name": "Alice"},
			{"id": 2, "name": "Bob"},
			{"id": 3, "name": "Charlie"}
		]
	}
	
	# Delete array item
	result = delete_from_json(json_doc, "users.1")
	assert len(result["users"]) == 2
	assert result["users"][0]["name"] == "Alice"
	assert result["users"][1]["name"] == "Charlie"
	assert len(json_doc["users"]) == 3  # Original should not change
	
	# Delete array item property
	result = delete_from_json(json_doc, "users.0.id")
	assert "id" not in result["users"][0]
	assert "name" in result["users"][0]
	assert "id" in json_doc["users"][0]  # Original should not change


def test_delete_complex_path():
	"""Test delete with complex paths."""
	json_doc = {
		"organization": {
			"departments": [
				{
					"name": "Engineering",
					"teams": [
						{"name": "Frontend", "members": 5},
						{"name": "Backend", "members": 8}
					]
				}
			]
		}
	}
	
	# Delete from nested structure
	result = delete_from_json(json_doc, "organization.departments.0.teams.1")
	assert len(result["organization"]["departments"][0]["teams"]) == 1
	assert result["organization"]["departments"][0]["teams"][0]["name"] == "Frontend"
	assert len(json_doc["organization"]["departments"][0]["teams"]) == 2  # Original should not change


def test_delete_errors():
	"""Test error cases for delete operation."""
	json_doc = {
		"name": "John",
		"users": [
			{"id": 1, "name": "Alice"}
		]
	}
	
	# Path not found
	with pytest.raises(KeyError):
		delete_from_json(json_doc, "address")
	
	# Invalid array index
	with pytest.raises(IndexError):
		delete_from_json(json_doc, "users.5")
	
	# Type error
	with pytest.raises(TypeError):
		delete_from_json(json_doc, "name.first")