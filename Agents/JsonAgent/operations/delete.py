"""
Delete operation for JSON documents.
"""
from typing import Dict, Any, List, Union
import copy
from .search import _parse_path


def delete_from_json(json_doc: Dict[str, Any], path: str) -> Dict[str, Any]:
	"""
	Delete an object from a JSON document at the specified path.
	
	Args:
		json_doc: JSON document
		path: Path to the object to delete
		
	Returns:
		Modified JSON document
	"""
	# Make a deep copy to avoid modifying the original
	result = copy.deepcopy(json_doc)
	
	# Parse the path
	path_segments = _parse_path(path)
	
	# Navigate to the target location
	current = result
	parent = None
	parent_segment = None
	
	for i, segment in enumerate(path_segments):
		if i == len(path_segments) - 1:
			# Last segment, delete the value
			if isinstance(current, dict):
				if segment in current:
					del current[segment]
				else:
					raise KeyError(f"Path segment '{segment}' not found in JSON document")
			elif isinstance(current, list):
				if segment.isdigit() and int(segment) < len(current):
					del current[int(segment)]
				else:
					raise IndexError(f"Index '{segment}' out of range or not a valid index")
			else:
				raise TypeError(f"Cannot delete value at path '{path}': parent is not a dict or list")
		else:
			# Navigate to the next segment
			parent = current
			parent_segment = segment
			
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
	
	return result 