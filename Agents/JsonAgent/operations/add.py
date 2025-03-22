"""
Add operation for JSON documents.
"""
from typing import Dict, Any, List, Union
import copy
from .search import _parse_path


def add_to_json(json_doc: Dict[str, Any], path: str, value: Any) -> Dict[str, Any]:
	"""
	Add an object to a JSON document at the specified path.
	
	Args:
		json_doc: JSON document
		path: Path where to add the object
		value: Value to add
		
	Returns:
		Modified JSON document
	"""
	# Make a deep copy to avoid modifying the original
	result = copy.deepcopy(json_doc)
	
	# Parse the path
	path_segments = _parse_path(path)
	
	# Navigate to the target location
	current = result
	for i, segment in enumerate(path_segments):
		if i == len(path_segments) - 1:
			# Last segment, add the value
			if isinstance(current, dict):
				current[segment] = value
			elif isinstance(current, list):
				if segment == "append":
					# Special case: append to list
					current.append(value)
				elif segment.isdigit():
					idx = int(segment)
					if idx <= len(current):
						current.insert(idx, value)
					else:
						raise IndexError(f"Index '{segment}' out of range for insertion")
				else:
					raise ValueError(f"Cannot add to list with non-numeric index: '{segment}'")
			else:
				raise TypeError(f"Cannot add value at path '{path}': parent is not a dict or list")
		else:
			# Navigate to the next segment
			if isinstance(current, dict):
				if segment not in current:
					# Create empty dict for missing segments
					current[segment] = {}
				current = current[segment]
			elif isinstance(current, list):
				if segment.isdigit() and int(segment) < len(current):
					current = current[int(segment)]
				else:
					raise IndexError(f"Index '{segment}' out of range or not a valid index")
			else:
				raise TypeError(f"Cannot navigate to path segment '{segment}': parent is not a dict or list")
	
	return result 