"""
Info operation for JSON documents.
"""
from typing import Dict, Any, Union
from .search import _parse_path


def get_json_info(json_doc: Dict[str, Any], path: str) -> str:
	"""
	Get information about an object or array at the specified path in a JSON document.
	
	Args:
		json_doc: JSON document
		path: Path to the object or array
		
	Returns:
		String describing the object's keys or array's size
	"""
	# Parse the path
	path_segments = _parse_path(path)
	
	# Navigate to the target location
	current = json_doc
	for segment in path_segments:
		if isinstance(current, dict):
			if segment in current:
				current = current[segment]
			else:
				raise KeyError(f"Path segment '{segment}' not found in JSON document")
		elif isinstance(current, list):
			if segment.isdigit() and int(segment) < len(current):
				current = current[int(segment)]
			else:
				raise IndexError(f"Index '{segment}' out of range or not a valid index")
		else:
			raise TypeError(f"Cannot navigate to path segment '{segment}': parent is not a dict or list")
	
	# Get info based on the type
	if isinstance(current, dict):
		if not current:
			return "Object: EMPTY"
		return f"Object with keys: {list(current.keys())}"
	elif isinstance(current, list):
		if not current:
			return "Array: EMPTY"
		return f"Array with size: {len(current)}"
	else:
		raise TypeError(f"Path '{path}' points to a primitive value, not an object or array")