from typing import Optional, Callable, Awaitable, Dict, Any
import json

from tz_common import CustomUUID
from tz_common.logs import log

from .blockCache import BlockCache, ObjectType
from .blockManager import BlockManager
from .blockDict import BlockDict
from .utils import Utils
from .index import Index


class CacheOrchestrator:
	"""
	Centralizes all cache-related operations and implements cache-or-fetch patterns.
	Handles cache invalidation logic, TTL management, and cache coordination.
	"""

	def __init__(self, cache: BlockCache, block_manager: BlockManager, index: Index):

		self.cache = cache
		self.block_manager = block_manager
		self.index = index


	async def get_or_fetch_page(self, 
								page_id: CustomUUID, 
								fetcher_func: Callable[[], Awaitable[Dict[str, Any]]]) -> Optional[BlockDict]:
		"""
		Args:
			page_id: UUID of the page
			fetcher_func: Async function that fetches raw data from API
			
		Returns:
			BlockDict with page data or None if not found
		"""
		# Check cache first
		cached_content = self.cache.get_page(page_id)
		if cached_content is not None:
			# Parse and wrap cached content in BlockDict
			unfiltered_data = self.block_manager.parse_cache_content(cached_content)
			# Get proper integer ID from Index
			int_id = self.index.to_int(page_id)
			if int_id is None:
				log.error(f"Could not convert page UUID {page_id} to integer ID")
				return None
			block_dict = BlockDict()
			block_dict.add_block(int_id, unfiltered_data)
			return block_dict
		
		# Cache miss - fetch from API
		try:
			raw_data = await fetcher_func()
			
			# Process invalidation if we have last_edited_time
			if "last_edited_time" in raw_data and "id" in raw_data:
				response_uuid = CustomUUID.from_string(raw_data["id"])
				last_edited_time = raw_data["last_edited_time"]
				self.invalidate_if_expired(response_uuid, Utils.convert_date_to_timestamp(last_edited_time), ObjectType.PAGE)
			
			# Use BlockManager to process and store
			main_int_id = self.block_manager.process_and_store_block(raw_data, ObjectType.PAGE)
			
			# Get the stored data and return
			cached_content = self.cache.get_page(page_id)
			if cached_content:
				unfiltered_data = self.block_manager.parse_cache_content(cached_content)
				block_dict = BlockDict()
				block_dict.add_block(main_int_id, unfiltered_data)
				return block_dict
			
			return None
			
		except Exception as e:
			log.error(f"Error fetching page {page_id}: {e}")
			return None


	async def get_or_fetch_database(self, 
									database_id: CustomUUID, 
									fetcher_func: Callable[[], Awaitable[Dict[str, Any]]]) -> Optional[BlockDict]:
		"""
		TODO: Explain if it is needed to be generic?
		
		Args:
			database_id: UUID of the database
			fetcher_func: Async function that fetches raw data from API
			
		Returns:
			BlockDict with database data or None if not found
		"""
		# Check cache first
		cached_content = self.cache.get_database(database_id)
		if cached_content is not None:
			# Parse and wrap cached content in BlockDict
			unfiltered_data = self.block_manager.parse_cache_content(cached_content)
			# Get proper integer ID from Index
			int_id = self.index.to_int(database_id)
			if int_id is None:
				log.error(f"Could not convert database UUID {database_id} to integer ID")
				return None
			block_dict = BlockDict()
			block_dict.add_block(int_id, unfiltered_data)
			return block_dict
		
		# Cache miss - fetch from API
		try:
			raw_data = await fetcher_func()
			
			# Process invalidation if we have last_edited_time
			if "last_edited_time" in raw_data and "id" in raw_data:
				response_uuid = CustomUUID.from_string(raw_data["id"])
				last_edited_time = raw_data["last_edited_time"]
				self.invalidate_if_expired(response_uuid, Utils.convert_date_to_timestamp(last_edited_time), ObjectType.DATABASE)
			
			# Use BlockManager to process and store
			main_int_id = self.block_manager.process_and_store_block(raw_data, ObjectType.DATABASE)
			
			# Get the stored data and return
			cached_content = self.cache.get_database(database_id)
			if cached_content:
				unfiltered_data = self.block_manager.parse_cache_content(cached_content)
				block_dict = BlockDict()
				block_dict.add_block(main_int_id, unfiltered_data)
				return block_dict
			
			return None
			
		except Exception as e:
			log.error(f"Error fetching database {database_id}: {e}")
			return None


	async def get_or_fetch_block(self, 
								 block_id: CustomUUID, 
								 fetcher_func: Callable[[], Awaitable[Dict[str, Any]]]) -> Optional[BlockDict]:
		"""
		TODO: Explain if it is needed to be generic?
		
		Args:
			block_id: UUID of the block
			fetcher_func: Async function that fetches raw data from API
			
		Returns:
			BlockDict with block data or None if not found
		"""
		# Check cache first
		cached_content = self.cache.get_block(block_id)
		if cached_content is not None:
			# Parse and wrap cached content in BlockDict
			unfiltered_data = self.block_manager.parse_cache_content(cached_content)
			# Get proper integer ID from Index
			int_id = self.index.to_int(block_id)
			if int_id is None:
				log.error(f"Could not convert block UUID {block_id} to integer ID")
				return None
			block_dict = BlockDict()
			block_dict.add_block(int_id, unfiltered_data)
			return block_dict
		
		# Cache miss - fetch from API
		try:
			raw_data = await fetcher_func()
			
			# Process invalidation for child blocks if we have results
			if "results" in raw_data:
				for block_item in raw_data.get("results", []):
					block_item_id_str = block_item.get("id")
					block_item_last_edited = block_item.get("last_edited_time")
					if block_item_id_str and block_item_last_edited:
						block_item_uuid = CustomUUID.from_string(block_item_id_str)
						self.cache.invalidate_block_if_expired(block_item_uuid, block_item_last_edited)
			
			# Use BlockManager to process children response
			children_block_dict = self.block_manager.process_children_response(
				raw_data, block_id, ObjectType.BLOCK
			)
			
			return children_block_dict
			
		except Exception as e:
			log.error(f"Error fetching block {block_id}: {e}")
			return None


	def get_cached_search_results(self, 
								  query: str, 
								  filter_str: Optional[str] = None, 
								  start_cursor: Optional[CustomUUID] = None) -> Optional[BlockDict]:
		"""
		Args:
			query: Search query string
			filter_str: Optional filter string
			start_cursor: Optional pagination cursor
			
		Returns:
			BlockDict with search results or None if not cached
		"""
		cache_entry = self.cache.get_search_results(query, filter_str, start_cursor)
		if cache_entry is not None:
			# Parse JSON string back to dictionary (this is unfiltered data)
			cache_data = self.block_manager.parse_cache_content(cache_entry)
			
			# Wrap unfiltered search results in BlockDict
			block_dict = BlockDict()
			if isinstance(cache_data, dict) and "results" in cache_data:
				for i, result in enumerate(cache_data["results"]):
					result_id = result.get('id', i)  # Use result ID or index as fallback
					if not isinstance(result_id, int):
						result_id = i
					block_dict.add_block(result_id, result)
			return block_dict
		
		return None


	async def cache_search_results(self, 
								   query: str, 
								   results: Dict[str, Any], 
								   filter_str: Optional[str] = None, 
								   start_cursor: Optional[CustomUUID] = None, 
								   ttl: Optional[int] = None) -> BlockDict:
		"""
		Args:
			query: Search query string
			results: Raw search results from API
			filter_str: Optional filter string
			start_cursor: Optional pagination cursor
			ttl: Time to live for cache entry
			
		Returns:
			BlockDict with processed search results
		"""
		# Process invalidation for search results
		for result in results.get("results", []):
			result_id = result.get("id")
			result_object_type = result.get("object", ObjectType.BLOCK.value)
			last_edited_time = result.get("last_edited_time")
			
			if last_edited_time and result_id:
				result_uuid = CustomUUID.from_string(result_id)
				# Use appropriate invalidation method based on object type
				if result_object_type == ObjectType.DATABASE.value:
					self.cache.invalidate_database_if_expired(result_uuid, last_edited_time)
				elif result_object_type == ObjectType.PAGE.value:
					self.cache.invalidate_page_if_expired(result_uuid, last_edited_time)
				else:  # block or unknown
					self.cache.invalidate_block_if_expired(result_uuid, last_edited_time)
		
		# Use BlockManager to process and store search results
		block_dict = self.block_manager.process_and_store_search_results(
			query, results, filter_str, start_cursor, ttl
		)
		
		return block_dict


	def get_cached_database_query_results(self, 
										  database_id: CustomUUID, 
										  filter_str: Optional[str] = None, 
										  start_cursor: Optional[CustomUUID] = None) -> Optional[BlockDict]:
		"""
		Args:
			database_id: UUID of the database
			filter_str: Optional filter string
			start_cursor: Optional pagination cursor
			
		Returns:
			BlockDict with query results or None if not cached
		"""
		cache_entry = self.cache.get_database_query_results(database_id, filter_str, start_cursor)
		if cache_entry is not None:
			# Parse JSON string back to dictionary (this is unfiltered data)
			cache_data = self.block_manager.parse_cache_content(cache_entry)
			
			# Wrap unfiltered database query results in BlockDict
			block_dict = BlockDict()
			if isinstance(cache_data, dict) and "results" in cache_data:
				for i, result in enumerate(cache_data["results"]):
					result_id = result.get('id', i)  # Use result ID or index as fallback
					if not isinstance(result_id, int):
						result_id = i
					block_dict.add_block(result_id, result)
			return block_dict
		
		return None


	async def cache_database_query_results(self, 
											database_id: CustomUUID, 
											results: Dict[str, Any], 
											filter_str: Optional[str] = None, 
											start_cursor: Optional[CustomUUID] = None) -> BlockDict:
		"""
		Args:
			database_id: UUID of the database
			results: Raw query results from API
			filter_str: Optional filter string
			start_cursor: Optional pagination cursor
			
		Returns:
			BlockDict with processed query results
		"""
		# Database query results are pages, not blocks - invalidate if needed
		for page in results.get("results", []):
			page_id = page.get("id")
			last_edited_time = page.get("last_edited_time")
			if page_id and last_edited_time:
				page_uuid = CustomUUID.from_string(page_id)
				self.cache.invalidate_page_if_expired(page_uuid, last_edited_time)
		
		# Use BlockManager to process and store database query results
		block_dict = self.block_manager.process_and_store_database_query_results(
			database_id, results, filter_str, start_cursor
		)
		
		return block_dict


	def invalidate_if_expired(self, 
							  uuid: CustomUUID, 
							  last_edited_time: str, 
							  object_type: ObjectType) -> bool:
		"""
		Centralized invalidation logic for any object type.
		
		Args:
			uuid: UUID of the object
			last_edited_time: Last edited timestamp
			object_type: Type of the object
			
		Returns:
			True if object was invalidated, False otherwise
		"""
		if object_type == ObjectType.DATABASE:
			return self.cache.invalidate_database_if_expired(uuid, last_edited_time)
		elif object_type == ObjectType.PAGE:
			self.cache.invalidate_page_if_expired(uuid, last_edited_time)
			return True  # invalidate_page_if_expired doesn't return bool
		elif object_type == ObjectType.BLOCK:
			return self.cache.invalidate_block_if_expired(uuid, last_edited_time)
		else:
			log.error(f"Unknown object type for invalidation: {object_type}")
			return False


	def verify_object_type_or_raise(self, uuid: CustomUUID, expected_type: ObjectType) -> None:
		"""
		Args:
			uuid: The UUID to check
			expected_type: The expected ObjectType
			
		Raises:
			ValueError: If the UUID exists in cache but with a different object type
		"""
		self.cache.verify_object_type_or_raise(uuid, expected_type)


	def get_children_uuids(self, parent_uuid: CustomUUID) -> list[CustomUUID]:
		"""
		Args:
			parent_uuid: UUID of the parent block
			
		Returns:
			List of children UUIDs
		"""
		return self.cache.get_children_uuids(str(parent_uuid))


	def is_children_fetched_for_block(self, cache_key: str) -> bool:
		"""
		Args:
			cache_key: Cache key string for the block
			
		Returns:
			True if children were fetched, False otherwise
		"""
		return self.cache.get_children_fetched_for_block(cache_key)


	def get_cached_block_content(self, uuid: CustomUUID) -> Optional[dict]:
		"""
		Get cached block content and parse it.
		
		Args:
			uuid: UUID of the block
			
		Returns:
			Parsed block content dictionary or None if not cached
		"""
		cached_content = self.cache.get_block(uuid)
		if cached_content:
			return self.block_manager.parse_cache_content(cached_content)
		return None 