"""
Unit tests for search operation.
"""
import pytest
from ..operations.search import search_json


def test_search_basic():
	"""Test basic search functionality."""
	json_doc = {
		"name": "John",
		"age": 30,
		"address": {
			"street": "123 Main St",
			"city": "New York"
		}
	}
	
	# Simple path
	result = search_json(json_doc, "name")
	assert result == {"name": "John"}
	
	# Nested path
	result = search_json(json_doc, "address.city")
	assert result == {"address.city": "New York"}


def test_search_array():
	"""Test search with arrays."""
	json_doc = {
		"users": [
			{"id": 1, "name": "Alice"},
			{"id": 2, "name": "Bob"},
			{"id": 3, "name": "Charlie"}
		]
	}
	
	# Array index
	result = search_json(json_doc, "users.1")
	assert result == {"users.1": {"id": 2, "name": "Bob"}}
	
	# Array property
	result = search_json(json_doc, "users.0.name")
	assert result == {"users.0.name": "Alice"}


def test_search_wildcard():
	"""Test search with wildcards."""
	json_doc = {
		"users": [
			{"id": 1, "name": "Alice"},
			{"id": 2, "name": "Bob"},
			{"id": 3, "name": "Charlie"}
		],
		"settings": {
			"theme": "dark",
			"notifications": True
		}
	}
	
	# Wildcard for all array items
	result = search_json(json_doc, "users.*")
	assert len(result) == 3
	assert "users.0" in result
	assert "users.1" in result
	assert "users.2" in result
	
	# Wildcard for specific property in all array items
	result = search_json(json_doc, "users.*.name")
	assert len(result) == 3
	assert result["users.0.name"] == "Alice"
	assert result["users.1.name"] == "Bob"
	assert result["users.2.name"] == "Charlie"
	
	# Wildcard for object properties
	result = search_json(json_doc, "settings.*")
	assert len(result) == 2
	assert result["settings.theme"] == "dark"
	assert result["settings.notifications"] is True


def test_search_complex_path():
	"""Test search with complex paths."""
	json_doc = {
		"data": {
			"users": [
				{
					"id": 1,
					"profile": {
						"name": "Alice",
						"contacts": [
							{"type": "email", "value": "alice@example.com"},
							{"type": "phone", "value": "123-456-7890"}
						]
					}
				}
			]
		}
	}
	
	# Complex path with arrays and nested objects
	result = search_json(json_doc, "data.users.0.profile.contacts.*.value")
	assert len(result) == 2
	assert result["data.users.0.profile.contacts.0.value"] == "alice@example.com"
	assert result["data.users.0.profile.contacts.1.value"] == "123-456-7890"
	
	# Path not found
	result = search_json(json_doc, "data.users.1")
	assert result == {} 


def test_search_repeated_names():

	json_doc = {
		"zdec1001" : {
			"name" : "Rune Stone",
			"handler" :"generic",
			"types" : {
				"zdec1001" : {
					"templates" : {
						"zdec1001" : {
							"animation" : "objects/zdec1001.def",
							"mask" : [ "VV", "VB" ]
						}
					}
				}
			}
		},
		"zdec0005" : {
			"name" : "Rune Stone",
			"handler" :"generic",
			"types" : {
				"zdec0005" : {
					"templates" : {
						"zdec0005" : {
							"animation" : "objects/zdec0005.def",
							"mask" : [ "VV", "VB" ]
						}
					}
				}
			}
		}
	}
	
	# Also test the top-level name fields which should all be "Rune Stone"
	result = search_json(json_doc, "*.name")
	assert len(result) == 2  # There are 5 rune stones in the file
	
	for key, value in result.items():
		assert value == "Rune Stone"
	
	# Testing specifically for expected structures
	stone_ids = [ "zdec1001", "zdec0005"]
	
	for stone_id in stone_ids:
		assert f"{stone_id}.name" in result
		
	long_path_result = search_json(json_doc, "*.types.*.templates.*.animation")
	assert len(long_path_result) == 2
	assert "objects/zdec1001.def" in long_path_result.values()
	assert "objects/zdec0005.def" in long_path_result.values()
	
	

