from typing import Optional, Dict, Any
import json

from .asyncClientManager import AsyncClientManager
from tz_common.logs import log


class NotionAPIClient:
	"""
	Pure HTTP client for Notion API communication.
	Handles only raw API calls without any business logic, caching, or data processing.
	"""

	def __init__(self, notion_token: str, page_size: int = 10):
		"""
		Initialize the API client with authentication.
		
		Args:
			notion_token: Notion API token for authentication
			page_size: Default page size for paginated requests
		"""
		self.notion_token = notion_token
		self.page_size = page_size
		self.headers = {
			"Authorization": f"Bearer {self.notion_token}",
			"Notion-Version": "2022-06-28"
		}


	async def __aenter__(self):
		"""Async context manager entry."""
		await AsyncClientManager.initialize()
		return self


	async def __aexit__(self, exc_type, exc_val, exc_tb):
		"""Async context manager exit."""
		# Do not close the manager; it's shared globally.
		pass


	async def get_page_raw(self, page_id: str) -> Dict[str, Any]:
		"""
		Raw API call to get page details.
		
		Args:
			page_id: UUID string of the page
			
		Returns:
			Raw JSON response from Notion API
			
		Raises:
			Exception: If HTTP request fails or returns non-200 status
		"""
		url = f"https://api.notion.com/v1/pages/{page_id}"
		
		await AsyncClientManager.wait_for_next_request()
		client = await AsyncClientManager.get_client()
		response = await client.get(url, headers=self.headers, timeout=30.0)
		
		if response.status_code != 200:
			error_data = response.json()
			raise Exception(f"HTTP {response.status_code}: {error_data}")
		
		return response.json()


	async def get_database_raw(self, database_id: str) -> Dict[str, Any]:
		"""
		Raw API call to get database details.
		
		Args:
			database_id: UUID string of the database
			
		Returns:
			Raw JSON response from Notion API
			
		Raises:
			Exception: If HTTP request fails or returns non-200 status
		"""
		url = f"https://api.notion.com/v1/databases/{database_id}"
		
		await AsyncClientManager.wait_for_next_request()
		client = await AsyncClientManager.get_client()
		response = await client.get(url, headers=self.headers, timeout=30.0)
		
		if response.status_code != 200:
			error_data = response.json()
			raise Exception(f"HTTP {response.status_code}: {error_data}")
		
		return response.json()


	async def get_block_children_raw(self, block_id: str, start_cursor: Optional[str] = None, page_size: Optional[int] = None) -> Dict[str, Any]:
		"""
		Raw API call to get block children.
		
		Args:
			block_id: UUID string of the parent block
			start_cursor: Optional cursor for pagination
			page_size: Optional page size override
			
		Returns:
			Raw JSON response from Notion API
			
		Raises:
			Exception: If HTTP request fails or returns non-200 status
		"""
		actual_page_size = page_size or 20  # Use 20 as default like in original code
		url = f"https://api.notion.com/v1/blocks/{block_id}/children?page_size={actual_page_size}"
		
		if start_cursor is not None:
			url += f"&start_cursor={start_cursor}"
		
		await AsyncClientManager.wait_for_next_request()
		client = await AsyncClientManager.get_client()
		response = await client.get(url, headers=self.headers, timeout=30.0)
		
		if response.status_code != 200:
			error_data = response.json()
			raise Exception(f"HTTP {response.status_code}: {error_data}")
		
		return response.json()


	async def search_raw(self, query: str, filter_type: Optional[str] = None, start_cursor: Optional[str] = None, sort: str = "descending") -> Dict[str, Any]:
		"""
		Raw API call to search Notion.
		
		Args:
			query: Search query string
			filter_type: Optional filter type ("page", "database", etc.)
			start_cursor: Optional cursor for pagination
			sort: Sort direction ("ascending" or "descending")
			
		Returns:
			Raw JSON response from Notion API
			
		Raises:
			Exception: If HTTP request fails or returns non-200 status
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
			payload["start_cursor"] = start_cursor
		
		await AsyncClientManager.wait_for_next_request()
		client = await AsyncClientManager.get_client()
		response = await client.post(url, headers=self.headers, json=payload)
		
		if response.status_code != 200:
			error_data = response.json()
			raise Exception(f"HTTP {response.status_code}: {error_data}")
		
		return response.json()


	async def query_database_raw(self, database_id: str, filter_obj: Optional[Dict[str, Any]] = None, start_cursor: Optional[str] = None) -> Dict[str, Any]:
		"""
		Raw API call to query database.
		
		Args:
			database_id: UUID string of the database
			filter_obj: Optional filter object (already parsed)
			start_cursor: Optional cursor for pagination
			
		Returns:
			Raw JSON response from Notion API
			
		Raises:
			Exception: If HTTP request fails or returns non-200 status
		"""
		url = f"https://api.notion.com/v1/databases/{database_id}/query"
		payload = {
			"page_size": self.page_size,
		}
		
		if filter_obj:
			payload["filter"] = filter_obj
		
		if start_cursor is not None:
			payload["start_cursor"] = start_cursor
		
		await AsyncClientManager.wait_for_next_request()
		client = await AsyncClientManager.get_client()
		response = await client.post(url, headers=self.headers, json=payload)
		
		if response.status_code != 200:
			error_data = response.json()
			raise Exception(f"HTTP {response.status_code}: {error_data}")
		
		return response.json() 