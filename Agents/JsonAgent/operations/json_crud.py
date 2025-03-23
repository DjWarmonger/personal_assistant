"""
Main JsonCrud class for handling JSON document operations.
"""
from typing import Dict, Any, Optional, Union
import json
from .search import search_json
from .search_global import search_global
from .modify import modify_json
from .add import add_to_json
from .delete import delete_from_json


class JsonCrud:
	"""Agent for performing CRUD operations on JSON documents."""
	
	def __init__(self):
		"""Initialize JsonCrud."""
		pass
	
	def search(self, json_doc: Union[Dict[str, Any], str], path: str) -> Dict[str, Any]:
		"""
		Search for a path in a JSON document, supporting wildcards.
		
		Args:
			json_doc: JSON document as dict or string
			path: Path to search for, supporting wildcards
			
		Returns:
			Dictionary with paths as keys and found objects as values
		"""
		if isinstance(json_doc, str):
			json_doc = json.loads(json_doc)
			
		return search_json(json_doc, path)
	
	def search_global(self, json_doc: Union[Dict[str, Any], str], pattern: str, 
					 case_sensitive: bool = False) -> Dict[str, Any]:
		"""
		Search for keys and values in a JSON document that match a regex pattern.
		
		Args:
			json_doc: JSON document as dict or string
			pattern: Regular expression pattern to match
			case_sensitive: Whether the search should be case-sensitive
			
		Returns:
			Dictionary with full paths as keys and matching objects as values
		"""
		if isinstance(json_doc, str):
			json_doc = json.loads(json_doc)
			
		return search_global(json_doc, pattern, case_sensitive)
	
	def modify(self, json_doc: Union[Dict[str, Any], str], path: str, value: Any) -> Dict[str, Any]:
		"""
		Modify an object in a JSON document at the specified path.
		
		Args:
			json_doc: JSON document as dict or string
			path: Path to the object to modify
			value: New value to set
			
		Returns:
			Modified JSON document
		"""
		if isinstance(json_doc, str):
			json_doc = json.loads(json_doc)
			
		return modify_json(json_doc, path, value)
	
	def add(self, json_doc: Union[Dict[str, Any], str], path: str, value: Any) -> Dict[str, Any]:
		"""
		Add an object to a JSON document at the specified path.
		
		Args:
			json_doc: JSON document as dict or string
			path: Path where to add the object
			value: Value to add
			
		Returns:
			Modified JSON document
		"""
		if isinstance(json_doc, str):
			json_doc = json.loads(json_doc)
			
		return add_to_json(json_doc, path, value)
	
	def delete(self, json_doc: Union[Dict[str, Any], str], path: str) -> Dict[str, Any]:
		"""
		Delete an object from a JSON document at the specified path.
		
		Args:
			json_doc: JSON document as dict or string
			path: Path to the object to delete
			
		Returns:
			Modified JSON document
		"""
		if isinstance(json_doc, str):
			json_doc = json.loads(json_doc)
			
		return delete_from_json(json_doc, path) 