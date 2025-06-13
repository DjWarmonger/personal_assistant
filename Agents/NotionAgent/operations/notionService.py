from typing import Optional, Union
import json
import asyncio
from collections import deque

from tz_common import CustomUUID
from tz_common.logs import log

from .notionAPIClient import NotionAPIClient
from .cacheOrchestrator import CacheOrchestrator
from .index import Index
from .urlIndex import UrlIndex
from .blockCache import ObjectType
from .blockTree import BlockTree
from .blockHolder import BlockHolder
from .blockDict import BlockDict
from .blockManager import BlockManager
from .exceptions import (
	NotionServiceError, InvalidUUIDError, BlockTreeRequiredError,
	CacheRetrievalError, APIError, ObjectTypeVerificationError
)


class NotionService:
	"""
	Business logic layer for Notion operations.
	Orchestrates between HTTP client, cache, and utilities to provide high-level Notion functionality.
	"""

	def __init__(self, 
				 api_client: NotionAPIClient,
				 cache_orchestrator: CacheOrchestrator,
				 index: Index,
				 url_index: UrlIndex,
				 block_holder: BlockHolder,
				 block_manager: BlockManager,
				 landing_page_id: Optional[CustomUUID] = None):
		"""
		Initialize the NotionService with required dependencies.
		
		Args:
			api_client: HTTP client for Notion API calls
			cache_orchestrator: Cache management and orchestration
			index: UUID to integer ID mapping
			url_index: URL indexing functionality
			block_holder: Block processing and filtering
			block_manager: Block management operations
			landing_page_id: Default page ID when none specified
		"""
		self.api_client = api_client
		self.cache_orchestrator = cache_orchestrator
		self.index = index
		self.url_index = url_index
		self.block_holder = block_holder
		self.block_manager = block_manager
		self.landing_page_id = landing_page_id


	async def get_notion_page_details(self, 
									  page_id: Optional[Union[str, CustomUUID]] = None, 
									  database_id: Optional[Union[str, CustomUUID]] = None) -> BlockDict:
		"""
		Get page or database details with caching support.
		
		Args:
			page_id: Optional page ID to retrieve
			database_id: Optional database ID to retrieve
			
		Returns:
			BlockDict with page/database data
		"""
		current_page_id: Optional[CustomUUID] = None
		current_database_id: Optional[CustomUUID] = None

		if page_id is None and database_id is None:
			current_page_id = self.landing_page_id
		elif page_id is not None:
			current_page_id = self.index.resolve_to_uuid(page_id)
		elif database_id is not None:
			current_database_id = self.index.resolve_to_uuid(database_id)

		try:
			if current_page_id is not None:
				# Use cache orchestrator for page retrieval
				async def fetch_page():
					return await self.api_client.get_page_raw(str(current_page_id))
				
				result = await self.cache_orchestrator.get_or_fetch_page(current_page_id, fetch_page)
				if result is not None:
					return result
				else:
					raise CacheRetrievalError("page", str(current_page_id))

			if current_database_id is not None:
				# Use cache orchestrator for database retrieval
				async def fetch_database():
					return await self.api_client.get_database_raw(str(current_database_id))
				
				result = await self.cache_orchestrator.get_or_fetch_database(current_database_id, fetch_database)
				if result is not None:
					return result
				else:
					raise CacheRetrievalError("database", str(current_database_id))

			# If we get here, no valid ID was provided
			raise InvalidUUIDError("No valid page_id or database_id provided")

		except NotionServiceError:
			# Re-raise our custom exceptions as-is
			raise
		except Exception as e:
			# Wrap unexpected exceptions in APIError
			raise APIError("get_notion_page_details", e)


	async def _get_block_children(self, 
								 uuid: Union[str, CustomUUID], 
								 block_tree: Optional[BlockTree] = None) -> BlockDict:
		"""
		Internal method: Get children of a block that have already been fetched.
		
		Args:
			uuid: UUID of the parent block
			block_tree: Optional block tree for relationship tracking
			
		Returns:
			BlockDict with children data
		"""
		parent_uuid_obj = self.index.resolve_to_uuid(uuid)
		if not parent_uuid_obj:
			raise InvalidUUIDError(str(uuid))
		
		if block_tree is None:
			raise BlockTreeRequiredError("_get_block_children")

		# Get children UUIDs from cache orchestrator
		children_custom_uuids = self.cache_orchestrator.get_children_uuids(parent_uuid_obj)
		
		# Convert UUIDs to integer IDs
		children_int_ids_map = {}
		if children_custom_uuids:
			conversion_result = self.index.to_int(children_custom_uuids)
			if isinstance(conversion_result, dict):
				children_int_ids_map = conversion_result
			else:
				log.error(f"Expected dict from self.index.to_int for list, got {type(conversion_result)}")

		children_int_ids_list = list(children_int_ids_map.values())

		# Get cached content for each child (no recursive fetching)
		children_content_dict = {}
		for int_id in children_int_ids_list:
			# Get the UUID for this int_id
			child_uuid = self.index.get_uuid(int_id)
			if child_uuid:
				# Get cached content using the cache orchestrator method
				parsed_content = self.cache_orchestrator.get_cached_block_content(child_uuid)
				if parsed_content:
					children_content_dict[int_id] = parsed_content
				else:
					log.debug(f"No cached content found for child {int_id} (UUID: {child_uuid})")
					children_content_dict[int_id] = {}
			else:
				log.error(f"Could not find UUID for int_id {int_id}")
				children_content_dict[int_id] = {}

		if block_tree is not None and children_custom_uuids:
			block_tree.add_relationships(parent_uuid_obj, children_custom_uuids)
		
		# Return BlockDict
		block_dict = BlockDict()
		block_dict.update(children_content_dict)
		return block_dict


	async def get_block_content(self,
								block_id: Union[int, str, CustomUUID],
								start_cursor: Optional[Union[int, str, CustomUUID]] = None,
								block_tree: Optional[BlockTree] = None) -> BlockDict:
		"""
		Get block content with all children recursively using a simple, robust queue-based approach.
		This method is designed to be explicitly sequential to avoid concurrency issues.
		
		Args:
			block_id: ID of the block to retrieve
			start_cursor: Optional pagination cursor
			block_tree: Optional block tree for relationship tracking
			
		Returns:
			BlockDict with block data and all children
		"""
		if block_tree is None:
			raise BlockTreeRequiredError("get_block_content")

		uuid_obj = self.index.resolve_to_uuid(block_id)
		if uuid_obj is None:
			raise InvalidUUIDError(str(block_id))

		# Initialize result BlockDict and the processing queue
		all_blocks = BlockDict()
		queue = deque([(uuid_obj, True)]) # (uuid, is_root)
		visited_nodes = {uuid_obj}

		# --- Step 1: Get the root block's own content ---
		# The /children endpoint does not include the parent, so we fetch it separately.
		# This also serves as a check for a valid block_id before starting recursion.
		try:
			# We use get_notion_page_details as it correctly fetches a single block's content
			# (pages and blocks are structurally similar for this purpose).
			root_block_content = await self.get_notion_page_details(page_id=uuid_obj)
			if root_block_content:
				all_blocks.update(root_block_content)
				if block_tree:
					block_tree.add_parent(uuid_obj)
			else:
				# If we can't get the root block, there's nothing to do.
				raise CacheRetrievalError("block", str(uuid_obj))
		except Exception as e:
			log.error(f"Failed to retrieve root block {uuid_obj}: {e}")
			raise # Re-raise the exception to be caught by the client facade

		# --- Step 2: Sequentially fetch children ---
		while queue:
			current_uuid, is_root = queue.popleft()

			try:
				# Determine the start_cursor only for the root block on the first call
				cursor_for_fetch = start_cursor if is_root else None
				sc_uuid_obj = self.index.resolve_to_uuid(cursor_for_fetch) if cursor_for_fetch else None
				start_cursor_str = sc_uuid_obj.to_formatted() if sc_uuid_obj else None

				# Directly and sequentially call the API client. This is the core of the fix.
				raw_children_data = await self.api_client.get_block_children_raw(str(current_uuid), start_cursor_str)
				
				# Process the raw response to get children
				children_list = raw_children_data.get("results", [])
				if not children_list:
					continue

				# Process and store the batch of children
				children_uuids = self.block_manager.process_children_batch(children_list, current_uuid)
				
				# Add new children to the final result and the queue for further processing
				for child_uuid in children_uuids:
					if child_uuid not in visited_nodes:
						child_content = self.cache_orchestrator.get_cached_block_content(child_uuid)
						if child_content:
							child_int_id = self.index.to_int(child_uuid)
							if child_int_id:
								all_blocks.add_block(child_int_id, child_content)
								visited_nodes.add(child_uuid)
								# If the child has children, add it to the queue to be processed
								if child_content.get("has_children"):
									queue.append((child_uuid, False))
				
				# Update block tree relationships
				if block_tree:
					block_tree.add_relationships(current_uuid, children_uuids)

			except Exception as e:
				log.error(f"Error fetching or processing children for block {current_uuid}: {e}")
				# We continue processing other branches instead of failing the entire operation
				continue
		
		log.flow(f"Completed recursive block fetching. Total blocks retrieved: {len(all_blocks.to_dict())}")
		return all_blocks


	async def _get_all_children_recursively(self, 
										   block_identifier: Union[str, CustomUUID], 
										   block_tree: Optional[BlockTree] = None,
										   visited_nodes: Optional[set] = None) -> BlockDict:
		# This method is now obsolete and will be removed.
		# For now, return an empty dict to avoid breaking any remaining calls.
		log.error("Deprecated method _get_all_children_recursively was called.")
		return BlockDict()


	async def search_notion(self, 
							query: str, 
							filter_type: Optional[str] = None,
							start_cursor: Optional[Union[str, CustomUUID]] = None, 
							sort: str = "descending") -> BlockDict:
		"""
		Search Notion with caching support.
		
		Args:
			query: Search query string
			filter_type: Optional filter type
			start_cursor: Optional pagination cursor
			sort: Sort direction
			
		Returns:
			BlockDict with search results
		"""
		# Convert start_cursor to CustomUUID for cache operations
		start_cursor_uuid = None
		start_cursor_str = None
		if start_cursor is not None:
			start_cursor_uuid = self.index.resolve_to_uuid(start_cursor)
			if start_cursor_uuid:
				start_cursor_str = start_cursor_uuid.to_formatted()

		# Check cache first
		cached_result = self.cache_orchestrator.get_cached_search_results(query, filter_type, start_cursor_uuid)
		if cached_result is not None:
			return cached_result

		try:
			# Fetch from API
			raw_results = await self.api_client.search_raw(query, filter_type, start_cursor_str, sort)
			
			# Process and cache results
			ttl = 30 * 24 * 60 * 60  # 30 days
			result = await self.cache_orchestrator.cache_search_results(
				query, raw_results, filter_type, start_cursor_uuid, ttl
			)
			
			if len(raw_results.get("results", [])) > 0:
				log.flow(f"Found {len(raw_results['results'])} search results")
			else:
				log.flow("No search results found for this query")

			return result

		except Exception as e:
			raise APIError("search_notion", e)


	async def query_database(self, 
							 database_id: Union[str, CustomUUID], 
							 filter_obj: Optional[dict] = None, 
							 start_cursor: Optional[Union[str, CustomUUID]] = None) -> BlockDict:
		"""
		Query database with caching support.
		
		Args:
			database_id: ID of the database to query
			filter_obj: Optional filter object (already parsed)
			start_cursor: Optional pagination cursor
			
		Returns:
			BlockDict with query results
		"""
		# Convert database_id to CustomUUID
		if isinstance(database_id, str):
			db_uuid = CustomUUID.from_string(database_id)
		else:
			db_uuid = database_id
		
		# Get integer ID for error message (matching original format)
		int_id = self.index.to_int(db_uuid)
		
		# Verify object type
		try:
			self.cache_orchestrator.verify_object_type_or_raise(db_uuid, ObjectType.DATABASE)
		except ValueError as e:
			# Restore original error message format with int_id
			if int_id is not None:
				raise ValueError(f"Database {int_id} was expected to be a database but it is a different type")
			else:
				# Fallback if int_id conversion fails
				raise ObjectTypeVerificationError(str(db_uuid), "database", "unknown")

		# Convert start_cursor to CustomUUID for cache operations
		start_cursor_uuid = None
		start_cursor_str = None
		if start_cursor is not None:
			start_cursor_uuid = self.index.resolve_to_uuid(start_cursor)
			if start_cursor_uuid:
				start_cursor_str = start_cursor_uuid.to_formatted()

		# Create cache filter key
		cache_filter_key = json.dumps(filter_obj, sort_keys=True) if filter_obj else None
		
		# Check cache first
		cached_result = self.cache_orchestrator.get_cached_database_query_results(db_uuid, cache_filter_key, start_cursor_uuid)
		if cached_result is not None:
			return cached_result

		try:
			# Fetch from API
			raw_results = await self.api_client.query_database_raw(str(db_uuid), filter_obj, start_cursor_str)
			
			# Process and cache results
			result = await self.cache_orchestrator.cache_database_query_results(
				db_uuid, raw_results, cache_filter_key, start_cursor_uuid
			)
			
			return result

		except Exception as e:
			raise APIError("query_database", e) 