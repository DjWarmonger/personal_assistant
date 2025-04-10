# JsonCrud

A Python library for performing CRUD operations on JSON documents with path-based addressing.

## Features

- **Search**: Find values in JSON documents using path expressions with wildcard support
- **Modify**: Change values at specific paths in JSON documents
- **Add**: Add new values at specific paths in JSON documents
- **Delete**: Remove values from specific paths in JSON documents

## Usage

```python
from Agents.JsonAgent import JsonCrud

# Create an instance
json_crud = JsonCrud()

# Example JSON
json_doc = {
    "users": [
        {"id": 1, "name": "Alice"},
        {"id": 2, "name": "Bob"}
    ],
    "settings": {
        "theme": "dark"
    }
}

# Search with wildcards
results = json_crud.search(json_doc, "users.*.name")
# Returns: {"users.0.name": "Alice", "users.1.name": "Bob"}

# Modify a value
modified = json_crud.modify(json_doc, "settings.theme", "light")
# Returns a new JSON with modified value

# Add a new value
added = json_crud.add(json_doc, "settings.notifications", True)
# Returns a new JSON with added value

# Delete a value
deleted = json_crud.delete(json_doc, "users.0")
# Returns a new JSON with the specified value deleted
```

## Path Expressions

Paths follow dot notation:
- Simple properties: `property_name`
- Nested properties: `parent.child`
- Array indices: `array.0`
- Wildcards: `users.*.name`

## Notes

- All operations return a new JSON document without modifying the original
- Path segments that don't exist will raise appropriate exceptions
- Array indices are zero-based 