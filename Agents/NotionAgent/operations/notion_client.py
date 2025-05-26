from dotenv import load_dotenv
import os
import asyncio
import json
from typing import Optional, Union

from tz_common import CustomUUID
from .asyncClientManager import AsyncClientManager
from .index import Index
from .urlIndex import UrlIndex
from .blockCache import BlockCache, ObjectType
from .blockTree import BlockTree
from .blockHolder import BlockHolder
from .blockDict import BlockDict
from tz_common.logs import log, LogLevel

from .utils import Utils

load_dotenv()
log.set_log_level(LogLevel.FLOW)

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_LANDING_PAGE_ID = os.getenv("NOTION_LANDING_PAGE_ID")

class NotionClient:
	key_to_type = {
		'id': ObjectType.BLOCK,
		'next_cursor': ObjectType.BLOCK,
		'block_id': ObjectType.BLOCK,
		'page_id': ObjectType.PAGE,
		'database_id': ObjectType.DATABASE
	}

	def __init__(self,
				 notion_token=NOTION_TOKEN,
				 landing_page_id=NOTION_LANDING_PAGE_ID,
				 load_from_disk=True,
				 run_on_start=True):
		
		raw_landing_page_id = landing_page_id
		if raw_landing_page_id:
			self.landing_page_id = CustomUUID.from_string(raw_landing_page_id)
		else:
			self.landing_page_id = None # Or raise an error if it's mandatory
		
		self.notion_token = notion_token

		self.index = Index(load_from_disk=load_from_disk, run_on_start=run_on_start)
		self.cache = BlockCache(load_from_disk=load_from_disk, run_on_start=run_on_start)
		self.url_index = UrlIndex()
		self.block_holder = BlockHolder(self.index, self.url_index)

		# TODO: Delete items from blockTree when cache is invalidated?

		self.headers = {
			"Authorization": f"Bearer {self.notion_token}",
			"Notion-Version": "2022-06-28"
		}
		self.page_size = 10

	async def __aenter__(self):
		await AsyncClientManager.initialize()
		return self

	async def __aexit__(self, exc_type, exc_val, exc_tb):
		# Do not close the manager; it's shared globally.
		pass


	async def get_notion_page_details(self, page_id: Optional[Union[str, CustomUUID]] = None, database_id: Optional[Union[str, CustomUUID]] = None) -> Union[BlockDict, str]:

		current_page_id: Optional[CustomUUID] = None
		current_database_id: Optional[CustomUUID] = None

		if page_id is None and database_id is None:
			current_page_id = self.landing_page_id
		elif page_id is not None:
			current_page_id = self.index.resolve_to_uuid(page_id) # resolve_to_uuid handles str or CustomUUID
		elif database_id is not None:
			current_database_id = self.index.resolve_to_uuid(database_id)

		try:
			if current_page_id is not None:
				# Example: check cache, etc.
				pass 

			if current_database_id is not None:
				cache_entry = self.cache.get_database(str(current_database_id))
				if cache_entry is not None:
					return cache_entry

			url_segment = str(current_page_id) if current_page_id else str(current_database_id)
			url_type = "pages" if current_page_id else "databases"
			url = f"https://api.notion.com/v1/{url_type}/{url_segment}"

			# Rate limiting + shared client usage
			await AsyncClientManager.wait_for_next_request()
			client = await AsyncClientManager.get_client()
			response = await client.get(url, headers=self.headers, timeout=30.0)

			if response.status_code != 200:
				log.error(response.status_code)
				error_dict = self.block_holder.clean_error_message(response.json())
				return f"HTTP {response.status_code}: {error_dict.get('message', 'Unknown error')}"
			else:
				raw_data = response.json() # Get raw data first
				original_response_id_str = raw_data.get("id") # Extract original ID string

				# Now convert the message for general processing (this will convert 'id' to int)
				data = self.block_holder.convert_message(raw_data, clean_timestamps=False)
				
				# Use the original_response_id_str for operations needing CustomUUID
				if original_response_id_str:
					try:
						response_uuid = CustomUUID.from_string(original_response_id_str)
						last_edited_time = raw_data.get("last_edited_time") # Get last_edited_time from raw_data too
						if last_edited_time is not None:
							self.cache.invalidate_page_if_expired(str(response_uuid), Utils.convert_date_to_timestamp(last_edited_time))
						self.index.visit_uuid(response_uuid)
					except ValueError as ve:
						log.error(f"Failed to convert original id {original_response_id_str} to CustomUUID: {ve}")

				# Clean timestamps on the already partially converted 'data'
				data = self.block_holder.clean_timestamps(data) 
				
				# Wrap in BlockDict for consistent return type
				block_dict = BlockDict()
				if isinstance(data, dict):
					# For page details, we treat the page as a single "block" with an artificial ID
					artificial_id = data.get('id', 0)  # Use the converted int ID if available
					if isinstance(artificial_id, int):
						block_dict.add_block(artificial_id, data)
					else:
						# Fallback: use 0 as artificial ID
						block_dict.add_block(0, data)
				
				return block_dict

		except ValueError as e:
			log.error(e)
			return str(e)
		

	async def get_block_children(self, uuid: Union[str, CustomUUID], block_tree: Optional[BlockTree] = None) -> Union[BlockDict, str]:
		"""
		This should be called only if we know that children have been already fetched.
		"""
		parent_uuid_obj = self.index.resolve_to_uuid(uuid)
		if not parent_uuid_obj:
			error_msg = f"Could not convert {uuid} to CustomUUID in get_block_children"
			log.error(error_msg)
			return error_msg
		
		if block_tree is None:
			error_msg = "block_tree is None in get_block_children"
			log.error(error_msg)
			return error_msg

		# get_children_uuids returns List[CustomUUID]
		children_custom_uuids = self.cache.get_children_uuids(str(parent_uuid_obj))
		
		# to_int now expects CustomUUID or List[CustomUUID]
		# We need to handle the case where children_custom_uuids might be empty
		children_int_ids_map = {} # Stores CustomUUID -> int representation
		if children_custom_uuids:
			# Assuming to_int called with a list returns a map {CustomUUID: int}
			conversion_result = self.index.to_int(children_custom_uuids)
			if isinstance(conversion_result, dict):
				children_int_ids_map = conversion_result
			else:
				log.error(f"Expected dict from self.index.to_int for list, got {type(conversion_result)}")

		# Convert map values (int ids) to a list for task creation
		children_int_ids_list = list(children_int_ids_map.values())

		async def get_child_content_by_int_id(int_id: int) -> tuple[int, dict]:
			child_content = await self.get_block_content(int_id, block_tree=block_tree, get_children=False)
			return int_id, child_content

		tasks = {int_id: get_child_content_by_int_id(int_id) for int_id in children_int_ids_list}
		gathered_children_content = await asyncio.gather(*tasks.values())
		
		children_content_dict = {int_id: content for int_id, content in gathered_children_content}

		if block_tree is not None and children_custom_uuids:
			block_tree.add_relationships(parent_uuid_obj, children_custom_uuids)
		
		# Return BlockDict instead of regular dict
		block_dict = BlockDict()
		block_dict.update(children_content_dict)
		return block_dict


	async def get_block_content(self,
							 block_id: Union[int, str, CustomUUID],
							 get_children=False,
							 start_cursor: Optional[Union[int, str, CustomUUID]] = None,
							 block_tree: Optional[BlockTree] = None) -> Union[BlockDict, str]:
		
		if block_tree is None:
			error_msg = "block_tree is None in get_block_content"
			log.error(error_msg)
			return error_msg

		uuid_obj = self.index.resolve_to_uuid(block_id)
		if uuid_obj is None:
			error_msg = f"Could not convert block_id {block_id} to UUID"
			log.error(error_msg)
			return error_msg
		
		# cache_key should use the string representation of CustomUUID
		current_cache_key_str = str(uuid_obj)
		url_uuid_str = str(uuid_obj) # For the API URL

		if block_tree is not None:
			# block_tree methods now expect CustomUUID
			# block_tree.add_parent(uuid_obj) # Potentially add here or after successful fetch
			pass

		url = f"https://api.notion.com/v1/blocks/{url_uuid_str}/children?page_size=20"
		if start_cursor is not None:
			sc_uuid_obj = self.index.resolve_to_uuid(start_cursor)
			if sc_uuid_obj:
				sc_formatted_uuid = sc_uuid_obj.to_formatted() # Pass CustomUUID here
				url += f"&start_cursor={sc_formatted_uuid}"
				current_cache_key_str = sc_formatted_uuid # Update cache key if start_cursor is used
			else:
				log.error(f"Could not format start_cursor {start_cursor}")

		cached_content = self.cache.get_block(current_cache_key_str) # get_block expects string

		if cached_content is not None:
			if not get_children:
				if block_tree is not None:
					# Ensure we add the correct CustomUUID object to the tree
					key_for_tree = sc_uuid_obj if start_cursor is not None and sc_uuid_obj else uuid_obj
					block_tree.add_parent(key_for_tree)
				
				# Wrap cached content in BlockDict for consistent return type
				block_dict = BlockDict()
				if isinstance(cached_content, dict):
					# Use a single artificial ID for the cached content
					artificial_id = cached_content.get('id', 0) if 'id' in cached_content else 0
					if not isinstance(artificial_id, int):
						artificial_id = 0
					block_dict.add_block(artificial_id, cached_content)
				return block_dict
			else:
				if self.cache.get_children_fetched_for_block(current_cache_key_str):
					# Ensure we pass the correct CustomUUID object for recursive call
					key_for_recursion = sc_uuid_obj if start_cursor is not None and sc_uuid_obj else uuid_obj
					return await self.get_all_children_recursively(key_for_recursion, block_tree)

		await AsyncClientManager.wait_for_next_request()
		client = await AsyncClientManager.get_client()
		response = await client.get(url, headers=self.headers, timeout=30.0)

		if response.status_code != 200:
			log.error(response.status_code)
			error_dict = self.block_holder.clean_error_message(response.json())
			return f"HTTP {response.status_code}: {error_dict.get('message', 'Unknown error')}"
		else:
			response_data_json = response.json()
			if block_tree is not None:
				key_for_tree_add = sc_uuid_obj if start_cursor is not None and sc_uuid_obj else uuid_obj
				block_tree.add_parent(key_for_tree_add)

			data_after_conversion = self.block_holder.convert_message(response_data_json,
							   clean_type=False,
							   clean_timestamps=False,
							   convert_to_index_id=False)
			
			if "results" not in data_after_conversion:
				log.error(f"No key 'results' when retrieving children for block {url_uuid_str}")
			else:
				for block_item in response_data_json.get("results", []):
					block_item_id_str = block_item.get("id")
					block_item_last_edited = block_item.get("last_edited_time")
					if block_item_id_str and block_item_last_edited:
						self.cache.invalidate_block_if_expired(block_item_id_str, block_item_last_edited)

				children_id_strs = [item["id"] for item in data_after_conversion.get("results", [])]

				for child_id_str, content_item in zip(children_id_strs, data_after_conversion.get("results", [])):
					processed_content = self.block_holder.convert_message(content_item)
					self.cache.add_block(child_id_str, processed_content) # add_block expects string UUID

				self.cache.add_parent_children_relationships(
					current_cache_key_str, # parent is identified by its cache key string
					children_id_strs,    # children are list of string IDs from response
					parent_type=ObjectType.BLOCK,
					child_type=ObjectType.BLOCK)
				
				if children_id_strs:
					self.cache.add_children_fetched_for_block(current_cache_key_str)

			final_data = self.block_holder.clean_type(data_after_conversion)
			final_data = self.block_holder.clean_timestamps(final_data)
			final_data = self.block_holder.convert_to_index_id(final_data)
			
			# Use current_cache_key_str for adding to cache, as it includes start_cursor if present
			self.cache.add_block(current_cache_key_str, final_data) 

			if get_children:
				log.flow("Retrieving children recursively for block " + str(current_cache_key_str))
				# Pass the original uuid_obj (or sc_uuid_obj if start_cursor was used) for recursion
				key_for_recursion_after_fetch = sc_uuid_obj if start_cursor is not None and sc_uuid_obj else uuid_obj
				final_data = await self.get_all_children_recursively(key_for_recursion_after_fetch, block_tree)
				return final_data

			# Wrap final_data in BlockDict for consistent return type when get_children=False
			block_dict = BlockDict()
			if isinstance(final_data, dict):
				# Use a single artificial ID for the final data
				artificial_id = final_data.get('id', 0) if 'id' in final_data else 0
				if not isinstance(artificial_id, int):
					artificial_id = 0
				block_dict.add_block(artificial_id, final_data)
			return block_dict
		
	
	async def get_all_children_recursively(self, block_identifier: Union[str, CustomUUID], block_tree: Optional[BlockTree] = None) -> Union[BlockDict, str]:
		"""
		Recursively fetch and flatten all children blocks for the given block identifier.
		Returns a BlockDict mapping each child block's id (int) to its content.
		"""
		parent_uuid_obj = self.index.resolve_to_uuid(block_identifier)
		if not parent_uuid_obj:
			error_msg = f"Could not convert {block_identifier} to CustomUUID in get_all_children_recursively"
			log.error(error_msg)
			return error_msg

		if block_tree is None:
			error_msg = "block_tree is None in get_all_children_recursively"
			log.error(error_msg)
			return error_msg

		# Initialize the flat BlockDict to accumulate all children
		flat_children_block_dict = BlockDict()
		
		# get_block_children now returns Union[BlockDict, str]
		immediate_children_result = await self.get_block_children(parent_uuid_obj, block_tree)
		
		# Handle error case
		if isinstance(immediate_children_result, str):
			return immediate_children_result  # Return error string
		
		# immediate_children_result is now a BlockDict
		immediate_children_content_map = immediate_children_result

		# Add immediate children to flat dict
		for child_int_id, child_content in immediate_children_content_map.items():
			flat_children_block_dict.add_block(child_int_id, child_content)
			
			# For recursion, we need the CustomUUID of the child.
			# We get child_int_id from immediate_children_content_map. We need to convert this int_id back to CustomUUID.
			child_uuid_obj_for_recursion = self.index.get_uuid(child_int_id) # get_uuid returns CustomUUID or None
			if child_uuid_obj_for_recursion:
				descendants_result = await self.get_all_children_recursively(child_uuid_obj_for_recursion, block_tree)
				
				# Handle error case from recursion
				if isinstance(descendants_result, str):
					log.error(f"Error in recursive call for child {child_int_id}: {descendants_result}")
					continue  # Skip this child's descendants but continue with other children
				
				# descendants_result is a BlockDict, update our flat dict
				flat_children_block_dict.update(descendants_result.to_dict())
			else:
				log.error(f"Could not find CustomUUID for int_id {child_int_id} during recursion")

		return flat_children_block_dict


	async def search_notion(self, query, filter_type=None,
							start_cursor: Optional[Union[str, CustomUUID]] = None, sort="descending") -> Union[BlockDict, str]:

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
			custom_uuid_obj = self.index.resolve_to_uuid(start_cursor)
			payload["start_cursor"] = custom_uuid_obj.to_formatted() if custom_uuid_obj else None


		cache_entry = self.cache.get_search_results(query, filter_type, str(start_cursor) if start_cursor else None)
		if cache_entry is not None:
			# Wrap cached search results in BlockDict
			block_dict = BlockDict()
			if isinstance(cache_entry, dict) and "results" in cache_entry:
				for i, result in enumerate(cache_entry["results"]):
					result_id = result.get('id', i)  # Use result ID or index as fallback
					if not isinstance(result_id, int):
						result_id = i
					block_dict.add_block(result_id, result)
			return block_dict

		await AsyncClientManager.wait_for_next_request()
		client = await AsyncClientManager.get_client()
		response = await client.post(url, headers=self.headers, json=payload)

		try:
			response_json = response.json()

			if response.status_code != 200:
				log.error(response.status_code)
				error_dict = self.block_holder.clean_error_message(response_json)
				return f"HTTP {response.status_code}: {error_dict.get('message', 'Unknown error')}"
			
			cache_key = self.cache.create_search_results_cache_key(query, filter_type, str(start_cursor) if start_cursor else None)
			
			#log.common(response_json)

			block_ids = [block["id"] for block in response_json["results"]]

			# TODO: Make sure children are actually blocks
			# TODO: Handle pages or maybe db if they are not blocks

			# TODO: Check if parent type set by AI is actually correct (was BLOCK)
			self.cache.add_parent_children_relationships(
				cache_key,
				block_ids,
				parent_type=ObjectType.SEARCH_RESULTS, # Corrected parent type
				child_type=ObjectType.BLOCK)
				# TODO: Invalidate cache is any children is modified. But not here, as we're going to add it to cache anyway.

			# Invalidate each child with last_edited_time
			for block in response_json["results"]:
				self.cache.invalidate_block_if_expired(block["id"], block["last_edited_time"])

				# TODO: Invalidate cache for all matching parent searches, not just one exact query

			log.flow("Converting message")
			data = self.block_holder.convert_message(response_json)

			if len(data["results"]) > 0:
				log.flow(f"Found {len(data['results'])} search results")
			else:
				log.flow("No search results found for this query")


			# Max ttl for search results is 30 days
			self.cache.add_search_results(query, data, filter_type, str(start_cursor) if start_cursor else None, ttl = 30 * 24 * 60 * 60)

			# Wrap search results in BlockDict
			block_dict = BlockDict()
			if isinstance(data, dict) and "results" in data:
				for i, result in enumerate(data["results"]):
					result_id = result.get('id', i)  # Use result ID or index as fallback
					if not isinstance(result_id, int):
						result_id = i
					block_dict.add_block(result_id, result)
			
			return block_dict

		except Exception as e:
			log.error(f"Error processing search response: {str(e)}")
			return f"Error processing search response: {str(e)}"


	async def query_database(self, database_id: Union[str, CustomUUID], filter=None, start_cursor: Optional[Union[str, CustomUUID]] = None) -> Union[BlockDict, str]:
		db_id_str = str(database_id) # Ensure database_id is string for cache and URL
		# FIXME: Verify if id is known in index but is NOT a database

		filter_obj = self.parse_filter(filter)

		url = f"https://api.notion.com/v1/databases/{db_id_str}/query"
		payload = {
			"page_size": self.page_size,
		}
		if filter_obj: # Use the parsed/validated filter_obj
			payload["filter"] = filter_obj
		if start_cursor is not None:
			custom_uuid_obj = self.index.resolve_to_uuid(start_cursor)
			payload["start_cursor"] = custom_uuid_obj.to_formatted() if custom_uuid_obj else None

		# Use a consistent key for caching that reflects the actual filter object used
		cache_filter_key = json.dumps(filter_obj, sort_keys=True) if filter_obj else None
		cache_entry = self.cache.get_database_query_results(db_id_str, cache_filter_key, str(start_cursor) if start_cursor else None)
		if cache_entry is not None:
			# Wrap cached database query results in BlockDict
			block_dict = BlockDict()
			if isinstance(cache_entry, dict) and "results" in cache_entry:
				for i, result in enumerate(cache_entry["results"]):
					result_id = result.get('id', i)  # Use result ID or index as fallback
					if not isinstance(result_id, int):
						result_id = i
					block_dict.add_block(result_id, result)
			return block_dict

		await AsyncClientManager.wait_for_next_request()
		client = await AsyncClientManager.get_client()
		response = await client.post(url, headers=self.headers, json=payload)

		if response.status_code != 200:
			error_message = self.block_holder.clean_error_message(response.json())
			log.error(response.status_code, error_message)
			return f"HTTP {response.status_code}: {error_message.get('message', 'Unknown error')}"
		else:
			# TODO: Invalidate blocks recursively if they are not up to date
			data = self.block_holder.convert_message(response.json(), clean_timestamps=False, convert_to_index_id=False)

			for block in data["results"]:
				if "last_edited_time" in block:
					self.cache.invalidate_block_if_expired(block["id"], block["last_edited_time"])

			final_data = self.block_holder.convert_to_index_id(self.block_holder.clean_timestamps(data))
			
			# Wrap database query results in BlockDict
			block_dict = BlockDict()
			if isinstance(final_data, dict) and "results" in final_data:
				for i, result in enumerate(final_data["results"]):
					result_id = result.get('id', i)  # Use result ID or index as fallback
					if not isinstance(result_id, int):
						result_id = i
					block_dict.add_block(result_id, result)
			
			return block_dict


	def set_favourite(self, uuid: int | list[int], set: bool) -> str:

		message = self.index.set_favourite_int(uuid, set)
		return message


	def _generate_notion_url(self, notion_id):
		if notion_id is None:
			return None
		
		base_url = "https://www.notion.so/"
		formatted_id = notion_id.replace("-", "")
		
		return f"{base_url}{formatted_id}"


	def parse_filter(self, filter: Optional[dict | str]) -> dict:
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
			filter: The filter to parse. Can be a Python dictionary,
			        a JSON string, or None.

		Returns:
			A Python dictionary representing the filter, ready for API request.
		"""
		if filter is None:
			filter_obj = {}
		elif isinstance(filter, str):
			try:
				filter_obj = json.loads(filter)
			except json.JSONDecodeError:
				log.error(f"Failed to parse filter string as JSON: ", filter)
				# Fallback to an empty filter or handle error appropriately
				filter_obj = {}
		elif isinstance(filter, dict):
			filter_obj = filter
		else:
			log.error(f"Filter is of unexpected type {type(filter)}.", "Using empty filter.")
			filter_obj = {}
	
		return filter_obj



