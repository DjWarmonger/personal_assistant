from typing import Union
from tz_common import CustomUUID
from tz_common.logs import log


class BlockHolder:
	"""
	Handles block processing, cleaning, and conversion operations.
	This class contains methods for cleaning and converting Notion API responses.
	"""

	def __init__(self, index, url_index):
		self.index = index
		
		# TODO: Refactor, do not keep url_index in the class
		self.url_index = url_index


	def convert_message(self,
						message: dict | list,
						clean_timestamps: bool = True,
						clean_type: bool = True,
						convert_to_index_id: bool = True,
						convert_urls: bool = True) -> dict | list:
		"""
		Main method to convert and clean Notion API messages.
		"""
		message = self.clean_response_details(message)
		if convert_to_index_id:
			message = self.convert_to_index_id(message)
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


	def convert_to_index_id(self, message):
		"""
		Convert UUID strings to integer IDs using the index.
		"""
		if isinstance(message, dict):
			for key, value in message.items():
				if key in ['id', 'next_cursor', 'page_id', 'database_id', 'block_id']:
					# Property ids are short, ignore them
					if isinstance(value, str) and CustomUUID.validate(value):
						uuid_obj = CustomUUID.from_string(value)
						int_id = self.index.add_uuid(uuid_obj)  # add_uuid expects CustomUUID
						message[key] = int_id
					else:
						# Silently ignore non-uuids or already converted ints
						if isinstance(value, int):
							pass  # Already an int, do nothing
						else:
							# Silently ignore other non-UUID string cases
							pass
				else:
					self.convert_to_index_id(value)
		elif isinstance(message, list):
			for item in message:
				self.convert_to_index_id(item)

		return message


	def convert_urls_to_id(self, message):
		"""
		Remove or convert URLs in the message.
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