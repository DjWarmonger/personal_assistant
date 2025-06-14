from typing import Optional, Dict, Union, List
import json
from tz_common import CustomUUID
from tz_common.logs import log

from .blockCache import BlockCache, ObjectType
from .index import Index
from .blockHolder import BlockHolder, FilteringOptions
from .blockDict import BlockDict


class BlockManager:
	"""
	Centralizes block processing and acts as interface between NotionClient and cache/index.
	Handles UUID extraction, index registration, and data conversion.
	"""

	def __init__(self, index: Index, cache: BlockCache, block_holder: BlockHolder):
		self.index = index
		self.cache = cache
		self.block_holder = block_holder


	def parse_cache_content(self, cache_content: str) -> dict:
		"""
		Parse JSON string from cache back to dictionary.
		
		Args:
			cache_content: Content retrieved from cache (JSON string or dict)
			
		Returns:
			Parsed dictionary or original content if parsing fails
		"""
		if isinstance(cache_content, str):
			try:
				return json.loads(cache_content)
			except json.JSONDecodeError:
				return cache_content
		return cache_content


	def process_and_store_block(self, 
								raw_data: dict, 
								object_type: ObjectType, 
								parent_uuid: Optional[CustomUUID] = None,
								parent_type: ObjectType = ObjectType.BLOCK) -> int:
		"""
		Process raw Notion API data and store it in cache with proper relationships.
		Stores unfiltered data with only UUID conversion.
		
		Args:
			raw_data: Raw JSON data from Notion API
			object_type: Type of the main object (BLOCK, PAGE, DATABASE, etc.)
			parent_uuid: UUID of parent object if this is a child
			parent_type: Type of parent object
			
		Returns:
			Integer ID of the main processed object
		"""
		# Extract all UUIDs from the raw data
		all_uuids = self.block_holder.extract_all_uuids(raw_data)
		
		# Register all UUIDs with the index and create mapping
		uuid_to_int_map = {}
		for uuid_obj in all_uuids:
			int_id = self.index.add_uuid(uuid_obj)
			uuid_to_int_map[uuid_obj] = int_id
		
		# Get the main object's UUID and int ID
		main_uuid_str = raw_data.get('id')
		if not main_uuid_str:
			raise ValueError("Raw data missing 'id' field")
		
		main_uuid = CustomUUID.from_string(main_uuid_str)
		main_int_id = uuid_to_int_map.get(main_uuid)
		if main_int_id is None:
			# Fallback: add to index if not found
			main_int_id = self.index.add_uuid(main_uuid)
		
		# Store unfiltered data with only UUID conversion
		# Convert UUIDs to int IDs but don't apply any filtering
		processed_data = self.block_holder.convert_uuids_to_int(raw_data.copy(), uuid_to_int_map)
		
		# Convert processed data to string for cache storage
		processed_data_str = json.dumps(processed_data) if isinstance(processed_data, dict) else str(processed_data)
		
		# Store in cache based on object type
		if object_type == ObjectType.BLOCK:
			self.cache.add_block(main_uuid, processed_data_str, parent_uuid=parent_uuid, parent_type=parent_type)
		elif object_type == ObjectType.PAGE:
			self.cache.add_page(main_uuid, processed_data_str)
		elif object_type == ObjectType.DATABASE:
			self.cache.add_database(main_uuid, processed_data_str)
		else:
			raise ValueError(f"Unsupported object type: {object_type}")
		
		# Add parent-child relationship if parent exists
		if parent_uuid is not None:
			self.cache.add_parent_child_relationship(
				parent_uuid, main_uuid, parent_type, object_type
			)
		
		log.debug(f"Processed and stored {object_type.value} {main_int_id}")
		return main_int_id


	def process_and_store_search_results(self,
										query: str,
										raw_results: dict,
										filter_str: Optional[str] = None,
										start_cursor: Optional[CustomUUID] = None,
										ttl: Optional[int] = None) -> BlockDict:
		"""
		Process search results and store them in cache.
		Stores unfiltered results with only UUID conversion.
		
		Returns:
			BlockDict containing the processed results (unfiltered)
		"""
		# Store original result data for relationship creation before processing
		original_results = []
		for result in raw_results.get("results", []):
			result_id = result.get("id")
			result_object_type = result.get("object", ObjectType.BLOCK.value)
			if result_id:
				original_results.append({
					"id": result_id,
					"object_type": result_object_type
				})
		
		# Extract UUIDs from all results
		all_uuids = self.block_holder.extract_all_uuids(raw_results)
		
		# Register UUIDs and create mapping
		uuid_to_int_map = {}
		for uuid_obj in all_uuids:
			int_id = self.index.add_uuid(uuid_obj)
			uuid_to_int_map[uuid_obj] = int_id
		
		# Store unfiltered data with only UUID conversion
		unfiltered_data = self.block_holder.convert_uuids_to_int(raw_results.copy(), uuid_to_int_map)
		
		# Store search results in cache (cache expects string content)
		unfiltered_data_str = json.dumps(unfiltered_data) if isinstance(unfiltered_data, dict) else str(unfiltered_data)
		self.cache.add_search_results(query, unfiltered_data_str, filter_str, start_cursor, ttl)
		
		# Create parent-child relationships for search results using original data
		cache_key = self.cache.create_search_results_cache_key(query, filter_str, start_cursor)
		for result_info in original_results:
			result_id = result_info["id"]
			result_object_type = result_info["object_type"]
			
			result_uuid = CustomUUID.from_string(result_id)
			
			# Map object type string to ObjectType enum
			if result_object_type == ObjectType.DATABASE.value:
				child_type = ObjectType.DATABASE
			elif result_object_type == ObjectType.PAGE.value:
				child_type = ObjectType.PAGE
			else:
				child_type = ObjectType.BLOCK
			
			# For search results, we need to use cache_key as parent_uuid
			# But add_parent_child_relationship expects CustomUUID, so we need a different approach
			# Let's use the cache's internal method that works with cache keys
			parent_key = cache_key
			child_key = self.cache.create_cache_key(str(result_uuid), child_type)
			
			# Use the cache's internal relationship method
			with self.cache.lock:
				self.cache.cursor.execute('''
					INSERT OR IGNORE INTO block_relationships (parent_key, child_key)
					VALUES (?, ?)
				''', (parent_key, child_key))
				self.cache.conn.commit()
				self.cache.set_dirty()
		
		# Convert to BlockDict for return (unfiltered)
		block_dict = BlockDict()
		if isinstance(unfiltered_data, dict) and "results" in unfiltered_data:
			for i, result in enumerate(unfiltered_data["results"]):
				result_id = result.get('id', i)
				if not isinstance(result_id, int):
					result_id = i
				block_dict.add_block(result_id, result)
		
		return block_dict


	def process_and_store_database_query_results(self,
												database_id: Union[str, CustomUUID],
												raw_results: dict,
												filter_str: Optional[str] = None,
												start_cursor: Optional[CustomUUID] = None) -> BlockDict:
		"""
		Process database query results and store them in cache.
		Stores unfiltered results with only UUID conversion.
		
		Returns:
			BlockDict containing the processed results (unfiltered)
		"""
		# Convert database_id to CustomUUID if needed
		if isinstance(database_id, str):
			db_uuid = CustomUUID.from_string(database_id)
		else:
			db_uuid = database_id
		
		# Extract UUIDs from all results
		all_uuids = self.block_holder.extract_all_uuids(raw_results)
		
		# Register UUIDs and create mapping
		uuid_to_int_map = {}
		for uuid_obj in all_uuids:
			int_id = self.index.add_uuid(uuid_obj)
			uuid_to_int_map[uuid_obj] = int_id
		
		# Store unfiltered data with only UUID conversion
		unfiltered_data = self.block_holder.convert_uuids_to_int(raw_results.copy(), uuid_to_int_map)
		
		# Convert processed data to string for cache storage
		unfiltered_data_str = json.dumps(unfiltered_data) if isinstance(unfiltered_data, dict) else str(unfiltered_data)
		
		# Store database query results in cache
		self.cache.add_database_query_results(db_uuid, unfiltered_data_str, filter_str, start_cursor)
		
		# Convert to BlockDict for return (unfiltered)
		block_dict = BlockDict()
		if isinstance(unfiltered_data, dict) and "results" in unfiltered_data:
			for i, result in enumerate(unfiltered_data["results"]):
				result_id = result.get('id', i)
				if not isinstance(result_id, int):
					result_id = i
				block_dict.add_block(result_id, result)
		
		return block_dict


	def process_children_batch(self,
							  children_data: List[dict],
							  parent_uuid: CustomUUID,
							  parent_type: ObjectType = ObjectType.BLOCK) -> List[CustomUUID]:
		"""
		Process a batch of children blocks and store them in cache.
		Stores unfiltered children data.
		
		Returns:
			List of children UUIDs
		"""
		children_uuids = []
		
		for child_data in children_data:
			child_id_str = child_data.get("id")
			if child_id_str:
				child_uuid = CustomUUID.from_string(child_id_str)
				children_uuids.append(child_uuid)
				
				# Process and store each child (now stores unfiltered data)
				self.process_and_store_block(
					child_data, 
					ObjectType.BLOCK, 
					parent_uuid=parent_uuid,
					parent_type=parent_type
				)
		
		# Add batch parent-children relationships
		if children_uuids:
			self.cache.add_parent_children_relationships(
				parent_uuid, children_uuids, parent_type, ObjectType.BLOCK
			)
			
			# Mark children as fetched for the parent
			parent_cache_key = self.cache.create_cache_key(str(parent_uuid), parent_type)
			self.cache.add_children_fetched_for_block(parent_cache_key)
		
		return children_uuids


	def process_children_response(self,
								 response_data: dict,
								 parent_uuid: CustomUUID,
								 parent_type: ObjectType = ObjectType.BLOCK) -> BlockDict:
		"""
		Process a children response from Notion API and return BlockDict with all children.
		
		Args:
			response_data: Raw response from /blocks/{id}/children endpoint
			parent_uuid: UUID of the parent block
			parent_type: Type of the parent object
			
		Returns:
			BlockDict containing all processed children (unfiltered)
		"""
		
		children_data = response_data.get("results", [])
		
		# Process all children (stores unfiltered data in cache)
		children_uuids = self.process_children_batch(children_data, parent_uuid, parent_type)
		
		# Create BlockDict with all children (unfiltered)
		block_dict = BlockDict()
		for child_uuid in children_uuids:
			# Get unfiltered content from cache
			cached_content = self.cache.get_block(child_uuid)
			if cached_content:
				unfiltered_data = self.parse_cache_content(cached_content)
				child_int_id = self.index.resolve_to_int(child_uuid)
				if child_int_id is not None:
					block_dict.add_block(child_int_id, unfiltered_data)
		
		return block_dict