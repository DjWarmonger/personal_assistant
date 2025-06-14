from typing import Union, Dict, List
from enum import Enum, auto
from tz_common import CustomUUID
from tz_common.logs import log


class FilteringOptions(Enum):
	"""
	Enum defining different filtering categories for Notion blocks.
	These can be combined to create custom filtering profiles.
	"""
	TIMESTAMPS = auto()  # Remove last_edited_time, created_time
	STYLE_ANNOTATIONS = auto()  # Remove bold, italic, strikethrough, underline, annotations, plain_text
	METADATA = auto()  # Remove icon, cover, archived, in_trash, last_edited_by, created_by
	EMPTY_VALUES = auto()  # Remove null/empty dict/list values
	TYPE_FIELDS = auto()  # Remove type fields
	URLS = auto()  # Remove/convert URL fields
	SYSTEM_FIELDS = auto()  # Remove request_id
	
	# Composite options
	MINIMAL = auto()  # TIMESTAMPS + STYLE_ANNOTATIONS + METADATA + EMPTY_VALUES
	AGENT_OPTIMIZED = auto()  # MINIMAL + TYPE_FIELDS + URLS + SYSTEM_FIELDS


class BlockHolder:
	"""
	Handles block processing, cleaning, and conversion operations.
	This class contains methods for cleaning and converting Notion API responses.
	"""

	def __init__(self, url_index):
		# TODO: Refactor, do not keep url_index in the class
		self.url_index = url_index


	@staticmethod
	def extract_all_uuids(message: Union[dict, list]) -> List[CustomUUID]:
		"""
		Extract all valid UUIDs from a message structure.
		Traverses the JSON and collects UUIDs from specific fields.
		"""
		uuids = []
		uuid_fields = ['id', 'next_cursor', 'page_id', 'database_id', 'block_id']
		
		def extract_from_object(obj):
			if isinstance(obj, dict):
				for key, value in obj.items():
					if key in uuid_fields:
						if isinstance(value, str) and CustomUUID.validate(value):
							try:
								uuid_obj = CustomUUID.from_string(value)
								uuids.append(uuid_obj)
							except ValueError:
								# Skip invalid UUIDs
								pass
					elif isinstance(value, (dict, list)):
						extract_from_object(value)
			elif isinstance(obj, list):
				for item in obj:
					extract_from_object(item)
		
		extract_from_object(message)
		return uuids


	def convert_uuids_to_int(self, message: dict | list, uuid_to_int_map: Dict[CustomUUID, int]) -> dict | list:
		"""
		Convert UUID strings to integer IDs using the provided mapping.
		This is separated from filtering to allow caching unfiltered data with int IDs.
		"""
		if isinstance(message, dict):
			for key, value in message.items():
				if key in ['id', 'next_cursor', 'page_id', 'database_id', 'block_id']:
					# Property ids are short, ignore them
					if isinstance(value, str) and CustomUUID.validate(value):
						try:
							uuid_obj = CustomUUID.from_string(value)
							if uuid_obj in uuid_to_int_map:
								message[key] = uuid_to_int_map[uuid_obj]
						except ValueError:
							# Skip invalid UUIDs
							pass
					# Silently ignore non-uuids or already converted ints
				else:
					self.convert_uuids_to_int(value, uuid_to_int_map)
		elif isinstance(message, list):
			for item in message:
				self.convert_uuids_to_int(item, uuid_to_int_map)

		return message


	def apply_filters(self, message: dict | list, filter_options: List[FilteringOptions]) -> dict | list:
		"""
		Apply specified filtering options to the message.
		This allows dynamic filtering without affecting cached data.
		"""
		# Expand composite options
		expanded_options = set()
		for option in filter_options:
			if option == FilteringOptions.MINIMAL:
				expanded_options.update([
					FilteringOptions.TIMESTAMPS,
					FilteringOptions.STYLE_ANNOTATIONS,
					FilteringOptions.METADATA,
					FilteringOptions.EMPTY_VALUES
				])
			elif option == FilteringOptions.AGENT_OPTIMIZED:
				expanded_options.update([
					FilteringOptions.TIMESTAMPS,
					FilteringOptions.STYLE_ANNOTATIONS,
					FilteringOptions.METADATA,
					FilteringOptions.EMPTY_VALUES,
					FilteringOptions.TYPE_FIELDS,
					FilteringOptions.URLS,
					FilteringOptions.SYSTEM_FIELDS
				])
			else:
				expanded_options.add(option)

		# Apply filters in order
		if FilteringOptions.METADATA in expanded_options or FilteringOptions.EMPTY_VALUES in expanded_options or FilteringOptions.SYSTEM_FIELDS in expanded_options:
			message = self._apply_metadata_and_system_filters(message, expanded_options)
		
		if FilteringOptions.URLS in expanded_options:
			message = self._apply_url_filters(message)
		
		if FilteringOptions.TIMESTAMPS in expanded_options:
			message = self._apply_timestamp_filters(message)
		
		if FilteringOptions.TYPE_FIELDS in expanded_options:
			message = self._apply_type_filters(message)

		return message


	def _apply_metadata_and_system_filters(self, message: dict | list, filter_options: set) -> dict | list:
		"""
		Apply metadata, empty values, and system field filters.
		"""
		def clean_object(obj):
			if isinstance(obj, dict):
				for key in list(obj.keys()):
					if FilteringOptions.EMPTY_VALUES in filter_options:
						if obj[key] is None:
							del obj[key]
							continue
						elif isinstance(obj[key], (dict, list)) and not obj[key]:
							del obj[key]
							continue
					
					if FilteringOptions.METADATA in filter_options:
						if key in ['icon', 'cover', 'bold', 'italic', 'strikethrough', 'underline', 'archived', 'in_trash', 'last_edited_by', 'created_by', 'annotations', 'plain_text']:
							del obj[key]
							continue
					
					if FilteringOptions.SYSTEM_FIELDS in filter_options:
						if key == 'request_id':
							del obj[key]
							continue
					
					if isinstance(obj[key], (dict, list)):
						clean_object(obj[key])
			elif isinstance(obj, list):
				for item in obj:
					clean_object(item)
		
		clean_object(message)
		return message


	def _apply_url_filters(self, message: dict | list) -> dict | list:
		"""
		Apply URL filtering.
		"""
		def convert_object(obj):
			if isinstance(obj, dict):
				for key in list(obj.keys()):
					if key in ["url", "href", "content"] and isinstance(obj[key], str):
						if self.url_index.is_url(obj[key]):
							del obj[key]
					elif isinstance(obj[key], (dict, list)):
						convert_object(obj[key])
			elif isinstance(obj, list):
				for item in obj:
					convert_object(item)

		convert_object(message)
		return message


	def _apply_timestamp_filters(self, message: dict | list) -> dict | list:
		"""
		Apply timestamp filtering.
		"""
		def clean_object(obj):
			if isinstance(obj, dict):
				for key in list(obj.keys()):
					if key in ["last_edited_time", "created_time"]:
						del obj[key]
					elif isinstance(obj[key], (dict, list)):
						clean_object(obj[key])
			elif isinstance(obj, list):
				for item in obj:
					clean_object(item)
		
		clean_object(message)
		return message


	def _apply_type_filters(self, message: dict | list) -> dict | list:
		"""
		Apply type field filtering.
		"""
		def clean_object(obj):
			if isinstance(obj, dict):
				for key in list(obj.keys()):
					if key == "type" and isinstance(obj[key], str):
						del obj[key]
					elif isinstance(obj[key], (dict, list)):
						clean_object(obj[key])
			elif isinstance(obj, list):
				for item in obj:
					clean_object(item)
		
		clean_object(message)
		return message


	def clean_error_message(self, message):
		"""
		Clean error messages from Notion API responses.
		"""
		if "object" in message:
			del message["object"]
		if "request_id" in message:
			del message["request_id"]

		return message


	def _filter_block_id(self, content: dict) -> dict:
		"""Remove block id field from content."""
		filtered = content.copy()
		if 'id' in filtered:
			del filtered['id']
		return filtered


	def _filter_parent_info(self, content: dict) -> dict:
		"""Remove parent information from content."""
		filtered = content.copy()
		if 'parent' in filtered:
			del filtered['parent']
		return filtered


	def _filter_has_children_info(self, content: dict) -> dict:
		"""Remove has_children field from content."""
		filtered = content.copy()
		if 'has_children' in filtered:
			del filtered['has_children']
		return filtered


	def apply_visited_blocks_filters(self, visited_blocks: dict, 
									remove_block_id: bool = True,
									remove_parent_info: bool = True, 
									remove_has_children: bool = True) -> dict:
		"""
		Apply filtering to visitedBlocks content for writer agent context.
		Each filter can be toggled independently for easy experimentation.
		
		Args:
			visited_blocks: Dictionary of block_id -> content
			remove_block_id: Whether to remove 'id' field
			remove_parent_info: Whether to remove 'parent' field  
			remove_has_children: Whether to remove 'has_children' field
			
		Returns:
			Filtered dictionary with same structure
		"""
		filtered_blocks = {}
		
		for block_id, content in visited_blocks.items():
			filtered_content = content.copy()
			
			if remove_block_id:
				filtered_content = self._filter_block_id(filtered_content)
				
			if remove_parent_info:
				filtered_content = self._filter_parent_info(filtered_content)
				
			if remove_has_children:
				filtered_content = self._filter_has_children_info(filtered_content)
				
			filtered_blocks[block_id] = filtered_content
		
		return filtered_blocks 