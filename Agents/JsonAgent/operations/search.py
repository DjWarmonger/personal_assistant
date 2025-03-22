"""
Search operation for JSON documents.
"""
from typing import Dict, Any, List, Tuple, Union
import re


def _parse_path(path: str) -> List[str]:
	"""
	Parse a path string into a list of path segments.
	
	Args:
		path: Path string (e.g., "users.0.name" or "users[0].name")
		
	Returns:
		List of path segments
	"""
	# Replace array notation with dot notation
	path = re.sub(r'\[(\w+)\]', r'.\1', path)
	return path.split('.')


def _get_value(obj: Dict[str, Any], path_segments: List[str]) -> Any:
	"""
	Get a value from a nested object using path segments.
	
	Args:
		obj: The object to search
		path_segments: List of path segments
		
	Returns:
		The value at the specified path or None if not found
	"""
	current = obj
	for segment in path_segments:
		if isinstance(current, dict) and segment in current:
			current = current[segment]
		elif isinstance(current, list) and segment.isdigit() and int(segment) < len(current):
			current = current[int(segment)]
		else:
			return None
	return current


def _match_wildcard(pattern: str, key: str) -> bool:
	"""
	Check if a key matches a wildcard pattern.
	
	Args:
		pattern: Pattern with wildcards (*)
		key: Key to match
		
	Returns:
		True if the key matches the pattern
	"""
	# Convert wildcard pattern to regex pattern
	regex_pattern = "^" + pattern.replace("*", ".*") + "$"
	return bool(re.match(regex_pattern, str(key)))


def _search_recursive(obj: Union[Dict[str, Any], List], path_segments: List[str], 
					 current_path: List[str] = None) -> Dict[str, Any]:
	"""
	Recursively search for paths in a JSON object.
	
	Args:
		obj: The object to search
		path_segments: List of path segments with possible wildcards
		current_path: Current path being evaluated
		
	Returns:
		Dictionary with found paths as keys and values
	"""
	if current_path is None:
		current_path = []
		
	results = {}
	
	if not path_segments:
		# Reached the end of the path, return the object at this point
		path_str = ".".join(current_path)
		results[path_str] = obj
		return results
		
	segment = path_segments[0]
	remaining_segments = path_segments[1:]
	
	# Handle wildcards
	if "*" in segment:
		if isinstance(obj, dict):
			for key in obj:
				if _match_wildcard(segment, key):
					new_path = current_path + [key]
					results.update(_search_recursive(obj[key], remaining_segments, new_path))
		elif isinstance(obj, list):
			for i, item in enumerate(obj):
				if _match_wildcard(segment, str(i)):
					new_path = current_path + [str(i)]
					results.update(_search_recursive(item, remaining_segments, new_path))
	else:
		# Normal segment
		if isinstance(obj, dict) and segment in obj:
			new_path = current_path + [segment]
			results.update(_search_recursive(obj[segment], remaining_segments, new_path))
		elif isinstance(obj, list) and segment.isdigit() and int(segment) < len(obj):
			idx = int(segment)
			new_path = current_path + [segment]
			results.update(_search_recursive(obj[idx], remaining_segments, new_path))
			
	return results


def search_json(json_doc: Dict[str, Any], path: str) -> Dict[str, Any]:
	"""
	Search for a path in a JSON document, supporting wildcards.
	
	Args:
		json_doc: JSON document
		path: Path to search for, with possible wildcards
		
	Returns:
		Dictionary with paths as keys and found objects as values
	"""
	path_segments = _parse_path(path)
	return _search_recursive(json_doc, path_segments) 