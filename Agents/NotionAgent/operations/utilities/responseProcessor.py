from typing import Dict, Any, List

from ..blockDict import BlockDict


class ResponseProcessor:
	"""
	Utility class for processing Notion API responses and converting them to BlockDict format.
	Handles common response processing patterns used across the system.
	"""

	@staticmethod
	def wrap_in_block_dict(data: Dict[str, Any], main_id: int) -> BlockDict:
		"""
		Wrap a single data object in a BlockDict with the specified ID.
		
		Args:
			data: The data dictionary to wrap
			main_id: The integer ID to use for the block
			
		Returns:
			BlockDict containing the data with the specified ID
		"""
		block_dict = BlockDict()
		block_dict.add_block(main_id, data)
		return block_dict


	@staticmethod
	def process_search_results_to_block_dict(results: Dict[str, Any]) -> BlockDict:
		"""
		Process search results from Notion API into BlockDict format.
		
		Args:
			results: Search results dictionary from Notion API
			
		Returns:
			BlockDict with search results mapped by index
		"""
		block_dict = BlockDict()
		
		if isinstance(results, dict) and "results" in results:
			for i, result in enumerate(results["results"]):
				# Use result ID if it's an integer, otherwise use index
				result_id = result.get('id', i)
				if not isinstance(result_id, int):
					result_id = i
				block_dict.add_block(result_id, result)
		
		return block_dict


	@staticmethod
	def process_database_query_results_to_block_dict(results: Dict[str, Any]) -> BlockDict:
		"""
		Process database query results from Notion API into BlockDict format.
		
		Args:
			results: Database query results dictionary from Notion API
			
		Returns:
			BlockDict with query results mapped by index
		"""
		block_dict = BlockDict()
		
		if isinstance(results, dict) and "results" in results:
			for i, result in enumerate(results["results"]):
				# Use result ID if it's an integer, otherwise use index
				result_id = result.get('id', i)
				if not isinstance(result_id, int):
					result_id = i
				block_dict.add_block(result_id, result)
		
		return block_dict


	@staticmethod
	def extract_results_list(response_data: Dict[str, Any]) -> List[Dict[str, Any]]:
		"""
		Extract the results list from a Notion API response.
		
		Args:
			response_data: Response data from Notion API
			
		Returns:
			List of result dictionaries, empty list if no results found
		"""
		if isinstance(response_data, dict) and "results" in response_data:
			results = response_data["results"]
			if isinstance(results, list):
				return results
		
		return []


	@staticmethod
	def has_more_results(response_data: Dict[str, Any]) -> bool:
		"""
		Check if the response indicates there are more results available.
		
		Args:
			response_data: Response data from Notion API
			
		Returns:
			True if there are more results, False otherwise
		"""
		return response_data.get("has_more", False)


	@staticmethod
	def get_next_cursor(response_data: Dict[str, Any]) -> str | None:
		"""
		Extract the next cursor for pagination from the response.
		
		Args:
			response_data: Response data from Notion API
			
		Returns:
			Next cursor string if available, None otherwise
		"""
		return response_data.get("next_cursor")


	@staticmethod
	def count_results(response_data: Dict[str, Any]) -> int:
		"""
		Count the number of results in the response.
		
		Args:
			response_data: Response data from Notion API
			
		Returns:
			Number of results in the response
		"""
		results = ResponseProcessor.extract_results_list(response_data)
		return len(results) 