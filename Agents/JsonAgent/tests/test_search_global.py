"""
Unit tests for global search operation.
"""
import pytest
import re
from ..operations.search_global import search_global


def test_search_global_basic():
	"""Test basic global search functionality."""
	json_doc = {
		"name": "John Smith",
		"age": 30,
		"address": {
			"street": "123 Main St",
			"city": "New York"
		}
	}
	
	# Search for values
	result = search_global(json_doc, "John")
	assert "name" in result
	assert result["name"] == "John Smith"
	
	# Search for keys
	result = search_global(json_doc, "name")
	assert "name" in result
	assert result["name"] == "John Smith"
	
	# Search with regex
	result = search_global(json_doc, "New.*")
	assert "address.city" in result
	assert result["address.city"] == "New York"


def test_search_global_nested():
	"""Test global search with nested structures."""
	json_doc = {
		"user": {
			"id": 12345,
			"profile": {
				"name": "Jane Doe",
				"email": "jane.doe@example.com"
			}
		},
		"settings": {
			"theme": "dark",
			"notifications": True
		}
	}
	
	# Search in nested objects
	result = search_global(json_doc, "example.com")
	assert "user.profile.email" in result
	assert result["user.profile.email"] == "jane.doe@example.com"
	
	# Search multiple matches
	result = search_global(json_doc, "profile|theme")
	assert len(result) == 2
	assert "user.profile" in result
	assert "settings.theme" in result
	assert result["settings.theme"] == "dark"


def test_search_global_arrays():
	"""Test global search with arrays."""
	json_doc = {
		"users": [
			{"id": 1, "name": "Alice", "skills": ["python", "javascript"]},
			{"id": 2, "name": "Bob", "skills": ["java", "python"]},
			{"id": 3, "name": "Charlie", "skills": ["go", "rust"]}
		]
	}
	
	# Search in arrays
	result = search_global(json_doc, "python")
	assert len(result) == 2
	assert "users.0.skills.0" in result
	assert "users.1.skills.1" in result
	
	# Search with case insensitivity
	result = search_global(json_doc, "ALICE", case_sensitive=False)
	assert "users.0.name" in result
	
	# Search with case sensitivity
	result = search_global(json_doc, "ALICE", case_sensitive=True)
	assert len(result) == 0


def test_search_global_numeric():
	"""Test global search with numeric values."""
	json_doc = {
		"data": [
			{"id": 1001, "value": 42.5},
			{"id": 1002, "value": 33.7},
			{"id": 1099, "value": 999}
		],
		"status": 200,
		"page": 1
	}
	
	# Search for numbers
	result = search_global(json_doc, "200")
	assert "status" in result
	assert result["status"] == 200
	
	# Search for partial numeric match
	result = search_global(json_doc, "100")
	assert len(result) == 2
	assert "data.0.id" in result
	assert "data.1.id" in result


def test_search_global_complex():
	"""Test global search with complex data structures."""
	json_doc = {
		"company": {
			"name": "Tech Solutions",
			"departments": [
				{
					"name": "Engineering",
					"employees": [
						{"id": "E001", "name": "Alex Smith", "projects": ["Alpha", "Beta"]},
						{"id": "E002", "name": "Sam Jones", "projects": ["Beta", "Gamma"]}
					]
				},
				{
					"name": "Marketing",
					"employees": [
						{"id": "M001", "name": "Taylor Brown", "campaigns": ["Summer Sale", "New Product"]}
					]
				}
			]
		}
	}
	
	# Deep nested search
	result = search_global(json_doc, "Beta")
	assert len(result) == 2
	assert "company.departments.0.employees.0.projects.1" in result
	assert "company.departments.0.employees.1.projects.0" in result
	
	# Search with complex regex
	result = search_global(json_doc, r"E\d+")
	assert len(result) == 2
	assert "company.departments.0.employees.0.id" in result
	assert "company.departments.0.employees.1.id" in result
	
	# Multi-word search
	result = search_global(json_doc, "New Product")
	assert len(result) == 1
	assert "company.departments.1.employees.0.campaigns.1" in result


def test_search_global_empty_results():
	"""Test global search with no matches."""
	json_doc = {
		"user": {
			"name": "John",
			"age": 30
		}
	}
	
	# No matches
	result = search_global(json_doc, "xyz123")
	assert result == {}


def test_search_global_empty_pattern():
	"""Test global search raises error with empty pattern."""
	json_doc = {"test": "value"}
	
	# Empty pattern should raise ValueError
	with pytest.raises(ValueError, match="Search pattern cannot be empty"):
		search_global(json_doc, "")
		
	# Whitespace-only pattern should also raise ValueError
	with pytest.raises(ValueError, match="Search pattern cannot be empty"):
		search_global(json_doc, "   ")


def test_search_global_edge_cases():
	"""Test global search with edge cases."""
	# Empty JSON
	result = search_global({}, "test")
	assert result == {}
	
	# JSON with null values
	json_doc = {
		"field1": None,
		"field2": "test",
		"field3": {
			"nested": None
		}
	}
	
	result = search_global(json_doc, "None")
	assert len(result) == 2
	assert "field1" in result
	assert "field3.nested" in result
	
	# JSON with boolean values
	json_doc = {
		"active": True,
		"verified": False
	}
	
	result = search_global(json_doc, "True")
	assert "active" in result
	assert result["active"] is True


def test_search_global_root_level():
	"""Test global search with matches at the root level."""
	# Test that root level is represented by empty string
	json_doc = "Root level string"
	
	result = search_global(json_doc, "Root")
	assert "" in result
	assert result[""] == "Root level string"
	
	# Test with an array at root level
	json_doc = ["item1", "item2", "matching item"]
	
	result = search_global(json_doc, "matching")
	assert "2" in result
	assert result["2"] == "matching item" 