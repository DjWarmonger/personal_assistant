"""
Global search operation for JSON documents.
"""
from typing import Dict, Any, List, Tuple, Union, Pattern
import re


def _search_recursive(obj: Union[Dict[str, Any], List, Any], 
					 pattern: Pattern, 
					 current_path: List[str] = None) -> Dict[str, Any]:
	"""
	Recursively search through a JSON object for keys or values matching a pattern.
	
	Args:
		obj: The object to search (dict, list, or primitive value)
		pattern: Compiled regex pattern to match against
		current_path: Current path being evaluated
		
	Returns:
		Dictionary with found paths as keys and corresponding values
	"""
	if current_path is None:
		current_path = []
		
	results = {}
	path_str = ".".join(current_path) if current_path else ""
	
	# Check if this object itself matches (for primitive values)
	if not isinstance(obj, (dict, list)):
		if pattern.search(str(obj)):
			results[path_str] = obj
			return results
			
	# Search within dictionaries
	if isinstance(obj, dict):
		for key, value in obj.items():
			# Check if key matches
			if pattern.search(str(key)):
				key_path = f"{path_str}.{key}" if path_str else key
				results[key_path] = value
				
			# Continue searching recursively
			new_path = current_path + [key]
			nested_results = _search_recursive(value, pattern, new_path)
			results.update(nested_results)
			
	# Search within lists
	elif isinstance(obj, list):
		for i, item in enumerate(obj):
			# Check if index matches (unlikely but possible)
			if pattern.search(str(i)):
				idx_path = f"{path_str}.{i}" if path_str else str(i)
				results[idx_path] = item
				
			# Continue searching recursively
			new_path = current_path + [str(i)]
			nested_results = _search_recursive(item, pattern, new_path)
			results.update(nested_results)
			
	return results


def search_global(json_doc: Dict[str, Any], pattern: str, 
				 case_sensitive: bool = False) -> Dict[str, Any]:
	"""
	Search for keys and values in a JSON document that match a regex pattern.
	
	Args:
		json_doc: JSON document to search
		pattern: Regular expression pattern to match
		case_sensitive: Whether the search should be case-sensitive
		
	Returns:
		Dictionary with full paths as keys and matching objects as values
		
	Raises:
		ValueError: If the pattern is empty or contains only whitespace
	"""
	if not pattern or pattern.strip() == "":
		raise ValueError("Search pattern cannot be empty")

	flags = 0 if case_sensitive else re.IGNORECASE
	compiled_pattern = re.compile(pattern, flags)
	
	results = _search_recursive(json_doc, compiled_pattern)
	
	# Remove the empty string entry if it exists and isn't meaningful
	# but keep it if the root object is a primitive value that matched
	if "" in results and isinstance(results[""], (dict, list)) and not isinstance(json_doc, (str, int, float, bool)):
		del results[""]
		
	return results
