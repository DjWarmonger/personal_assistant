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


	# Legacy methods - keep for backward compatibility during migration
	def convert_message(self,
						message: dict | list,
						clean_timestamps: bool = True,
						clean_type: bool = True,
						convert_to_index_id: bool = True,
						convert_urls: bool = True,
						uuid_to_int_map: Dict[CustomUUID, int] = None) -> dict | list:
		"""
		Main method to convert and clean Notion API messages.
		LEGACY METHOD - kept for backward compatibility during migration.
		"""
		message = self.clean_response_details(message)
		if convert_to_index_id and uuid_to_int_map is not None:
			message = self.convert_to_index_id(message, uuid_to_int_map)
		if convert_urls:
			message = self.convert_urls_to_id(message)
		if clean_timestamps:
			message = self.clean_timestamps(message)
		if clean_type:
			message = self.clean_type(message)
		return message


	def clean_response_details(self, message):
		"""
		Remove unnecessary details from Notion API responses.
		LEGACY METHOD - kept for backward compatibility during migration.
		"""
		def clean_object(obj):
			if isinstance(obj, dict):
				for key in list(obj.keys()):
					if obj[key] is None:
						del obj[key]
					elif isinstance(obj[key], (dict, list)) and not obj[key]:
						del obj[key]
					elif key in ['icon', 'cover', 'bold', 'italic', 'strikethrough', 'underline', 'archived', 'in_trash', 'last_edited_by', 'created_by', 'annotations', 'plain_text']:
						del obj[key]
					elif isinstance(obj[key], (dict, list)):
						clean_object(obj[key])
			elif isinstance(obj, list):
				for item in obj:
					clean_object(item)
		
		clean_object(message)
		if "request_id" in message:
			del message["request_id"]

		return message


	def convert_to_index_id(self, message, uuid_to_int_map: Dict[CustomUUID, int]):
		"""
		Convert UUID strings to integer IDs using the provided mapping.
		LEGACY METHOD - kept for backward compatibility during migration.
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
					self.convert_to_index_id(value, uuid_to_int_map)
		elif isinstance(message, list):
			for item in message:
				self.convert_to_index_id(item, uuid_to_int_map)

		return message


	def convert_urls_to_id(self, message):
		"""
		Remove or convert URLs in the message.
		LEGACY METHOD - kept for backward compatibility during migration.
		"""
		# TODO: Also handle internal Notions links:
		# 'plain_text': 'Metaprompt', 'href': '/1399efeb667680939950d25093855de5'}

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


	def clean_timestamps(self, message):
		"""
		Remove timestamp fields from the message.
		LEGACY METHOD - kept for backward compatibility during migration.
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


	def clean_type(self, message):
		"""
		Remove type fields from the message.
		LEGACY METHOD - kept for backward compatibility during migration.
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