import json
from typing import Optional, Dict, Any

from tz_common.logs import log


class FilterParser:
	"""
	Utility class for parsing and validating Notion API filters.
	Handles conversion of various filter input formats to proper dictionary format.
	"""

	@staticmethod
	def parse_filter(filter_input: Optional[Dict[str, Any] | str]) -> Dict[str, Any]:
		"""
		Parses the input filter into a Python dictionary to ensure correct
		serialization for the Notion API.

		The Notion API expects the 'filter' in a query request body to be a
		JSON object. If a string representation of a JSON object is passed
		directly to the HTTP client, it will be serialized as a JSON string,
		leading to a 400 validation error from Notion.

		This method handles:
		- None: Returns an empty dictionary (no filter).
		- String: Attempts to parse it as JSON. If parsing fails (e.g., malformed
		  JSON), logs an error and returns an empty dictionary.
		- Dictionary: Returns it directly.

		Args:
			filter_input: The filter to parse. Can be a Python dictionary,
			             a JSON string, or None.

		Returns:
			A Python dictionary representing the filter, ready for API request.
		"""
		if filter_input is None:
			filter_obj = {}
		elif isinstance(filter_input, str):
			try:
				filter_obj = json.loads(filter_input)
			except json.JSONDecodeError:
				log.error(f"Failed to parse filter string as JSON: ", filter_input)
				# Fallback to an empty filter or handle error appropriately
				filter_obj = {}
		elif isinstance(filter_input, dict):
			filter_obj = filter_input
		else:
			log.error(f"Filter is of unexpected type {type(filter_input)}.", "Using empty filter.")
			filter_obj = {}
	
		return filter_obj


	@staticmethod
	def validate_database_filter(filter_obj: Dict[str, Any]) -> bool:
		"""
		Validates that a filter object is suitable for database queries.
		
		Args:
			filter_obj: The filter dictionary to validate
			
		Returns:
			True if the filter is valid for database queries, False otherwise
		"""
		if not isinstance(filter_obj, dict):
			return False
		
		# Empty filter is always valid
		if not filter_obj:
			return True
		
		# Basic validation - check for required structure
		# Notion filters should have specific structure, but we'll keep this simple for now
		try:
			# If it can be serialized to JSON, it's probably valid
			json.dumps(filter_obj)
			return True
		except (TypeError, ValueError):
			return False 