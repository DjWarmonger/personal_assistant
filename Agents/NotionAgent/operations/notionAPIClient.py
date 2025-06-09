from typing import Optional, Dict, Any, Union
import json

from tz_common import CustomUUID
from tz_common.logs import log

from .asyncClientManager import AsyncClientManager
from .blockHolder import BlockHolder
from .utils import Utils
from .exceptions import HTTPError


class NotionAPIClient:
	"""
	Handles HTTP communication with the Notion API.
	Responsible for making API calls and handling HTTP-level concerns.
	"""

	def __init__(self, notion_token: str, block_holder: BlockHolder):
		self.notion_token = notion_token
		self.block_holder = block_holder
		self.headers = {
			"Authorization": f"Bearer {self.notion_token}",
			"Notion-Version": "2022-06-28"
		}
		self.page_size = 10


	def _handle_api_error(self, response, method_name: str) -> None:
		error_dict = self.block_holder.clean_error_message(response.json())
		log.error(response.status_code, error_dict)
		raise HTTPError(method_name, response.status_code)


	async def get_page_raw(self, page_id: CustomUUID) -> Dict[str, Any]:
		"""
		Fetch raw page data from Notion API.
		
		Args:
			page_id: UUID of the page to fetch
			
		Returns:
			Raw page data from API
		"""
		url = f"https://api.notion.com/v1/pages/{str(page_id)}"
		
		await AsyncClientManager.wait_for_next_request()
		client = await AsyncClientManager.get_client()
		response = await client.get(url, headers=self.headers, timeout=30.0)
		
		if response.status_code != 200:
			self._handle_api_error(response, "get_page_raw")
		
		return response.json()


	async def get_database_raw(self, database_id: CustomUUID) -> Dict[str, Any]:
		"""
		Fetch raw database data from Notion API.
		
		Args:
			database_id: UUID of the database to fetch
			
		Returns:
			Raw database data from API
		"""
		url = f"https://api.notion.com/v1/databases/{str(database_id)}"
		
		await AsyncClientManager.wait_for_next_request()
		client = await AsyncClientManager.get_client()
		response = await client.get(url, headers=self.headers, timeout=30.0)
		
		if response.status_code != 200:
			self._handle_api_error(response, "get_database_raw")
		
		return response.json()


	async def get_block_children_raw(self, block_id: CustomUUID, start_cursor: Optional[CustomUUID] = None) -> Dict[str, Any]:
		"""
		Fetch raw block children data from Notion API.
		
		Args:
			block_id: UUID of the block whose children to fetch
			start_cursor: Optional pagination cursor
			
		Returns:
			Raw children data from API
		"""
		url = f"https://api.notion.com/v1/blocks/{str(block_id)}/children?page_size=20"
		if start_cursor is not None:
			sc_formatted_uuid = start_cursor.to_formatted()
			url += f"&start_cursor={sc_formatted_uuid}"
		
		await AsyncClientManager.wait_for_next_request()
		client = await AsyncClientManager.get_client()
		response = await client.get(url, headers=self.headers, timeout=30.0)
		
		if response.status_code != 200:
			self._handle_api_error(response, "get_block_children_raw")
		
		return response.json()


	async def search_raw(self, query: str, filter_type: Optional[str] = None, 
						 start_cursor: Optional[CustomUUID] = None, sort: str = "descending") -> Dict[str, Any]:
		"""
		Perform raw search on Notion API.
		
		Args:
			query: Search query string
			filter_type: Optional filter type
			start_cursor: Optional pagination cursor
			sort: Sort direction
			
		Returns:
			Raw search results from API
		"""
		url = "https://api.notion.com/v1/search"
		payload = {
			"query": query,
			"page_size": self.page_size,
			"sort": {
				"direction": sort,
				"timestamp": "last_edited_time"
			}
		}
		if filter_type is not None:
			payload["filter"] = {
				"value": filter_type,
				"property": "object"
			}
		if start_cursor is not None:
			payload["start_cursor"] = start_cursor.to_formatted()

		await AsyncClientManager.wait_for_next_request()
		client = await AsyncClientManager.get_client()
		response = await client.post(url, headers=self.headers, json=payload)

		if response.status_code != 200:
			self._handle_api_error(response, "search_raw")
		
		return response.json()


	async def query_database_raw(self, database_id: CustomUUID, filter_obj: Optional[Dict[str, Any]] = None,
								 start_cursor: Optional[CustomUUID] = None) -> Dict[str, Any]:
		"""
		Perform raw database query on Notion API.
		
		Args:
			database_id: UUID of the database to query
			filter_obj: Optional filter object
			start_cursor: Optional pagination cursor
			
		Returns:
			Raw query results from API
		"""
		url = f"https://api.notion.com/v1/databases/{str(database_id)}/query"
		payload = {
			"page_size": self.page_size,
		}
		if filter_obj:
			payload["filter"] = filter_obj
		if start_cursor is not None:
			payload["start_cursor"] = start_cursor.to_formatted()

		await AsyncClientManager.wait_for_next_request()
		client = await AsyncClientManager.get_client()
		response = await client.post(url, headers=self.headers, json=payload)

		if response.status_code != 200:
			self._handle_api_error(response, "query_database_raw")
		
		return response.json()


	def parse_filter(self, filter_input: Optional[Union[dict, str]]) -> Optional[Dict[str, Any]]:
		"""
		Parse filter input into a proper dictionary for API requests.
		
		Args:
			filter_input: Filter as dict, JSON string, or None
			
		Returns:
			Parsed filter dictionary or None
		"""
		if filter_input is None:
			return None
		elif isinstance(filter_input, str):
			try:
				return json.loads(filter_input)
			except json.JSONDecodeError:
				log.error(f"Failed to parse filter string as JSON: {filter_input}")
				return None
		elif isinstance(filter_input, dict):
			return filter_input
		else:
			log.error(f"Filter is of unexpected type {type(filter_input)}. Using empty filter.")
			return None 