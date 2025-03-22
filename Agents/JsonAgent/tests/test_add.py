"""
Unit tests for add operation.
"""
import pytest
from ..operations.add import add_to_json


def test_add_basic():
	"""Test basic add functionality."""
	json_doc = {
		"name": "John",
		"age": 30
	}
	
	# Add new property
	result = add_to_json(json_doc, "address", {"street": "123 Main St", "city": "New York"})
	assert "address" in result
	assert result["address"]["city"] == "New York"
	assert "address" not in json_doc  # Original should not change
	
	# Add nested property
	result = add_to_json(json_doc, "profile.email", "john@example.com")
	assert "profile" in result
	assert result["profile"]["email"] == "john@example.com"
	assert "profile" not in json_doc  # Original should not change


def test_add_to_array():
	"""Test add with arrays."""
	json_doc = {
		"users": [
			{"id": 1, "name": "Alice"},
			{"id": 2, "name": "Bob"}
		]
	}
	
	# Add item to array by append
	result = add_to_json(json_doc, "users.append", {"id": 3, "name": "Charlie"})
	assert len(result["users"]) == 3
	assert result["users"][2]["name"] == "Charlie"
	assert len(json_doc["users"]) == 2  # Original should not change
	
	# Add item to array at index
	result = add_to_json(json_doc, "users.0", {"id": 0, "name": "Admin"})
	assert len(result["users"]) == 3
	assert result["users"][0]["name"] == "Admin"
	assert result["users"][1]["name"] == "Alice"
	assert len(json_doc["users"]) == 2  # Original should not change
	
	# Add property to array item
	result = add_to_json(json_doc, "users.0.email", "alice@example.com")
	assert "email" in result["users"][0]
	assert result["users"][0]["email"] == "alice@example.com"
	assert "email" not in json_doc["users"][0]  # Original should not change


def test_add_complex_path():
	"""Test add with complex paths."""
	json_doc = {
		"organization": {
			"departments": []
		}
	}
	
	# Add to nested structure with arrays
	result = add_to_json(json_doc, "organization.departments.append", {"name": "Engineering"})
	assert len(result["organization"]["departments"]) == 1
	assert result["organization"]["departments"][0]["name"] == "Engineering"
	
	# Create path with multiple missing segments
	result = add_to_json(json_doc, "settings.theme.colors.primary", "#336699")
	assert "settings" in result
	assert "theme" in result["settings"]
	assert "colors" in result["settings"]["theme"]
	assert result["settings"]["theme"]["colors"]["primary"] == "#336699"


def test_add_errors():
	"""Test error cases for add operation."""
	json_doc = {
		"name": "John",
		"contacts": ["email", "phone"]
	}
	
	# Invalid array index
	with pytest.raises(IndexError):
		add_to_json(json_doc, "contacts.10", "fax")
	
	# Invalid path type
	with pytest.raises(TypeError):
		add_to_json(json_doc, "name.first", "John") 