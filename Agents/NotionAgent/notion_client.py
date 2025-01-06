from dotenv import load_dotenv
import os

from asyncClientManager import AsyncClientManager
from index import Index
from urlIndex import UrlIndex
from blockCache import BlockCache, ObjectType
from tz_common.logs import log, LogLevel

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
				 run_on_start=True):
		self.landing_page_id = landing_page_id
		self.notion_token = notion_token

		self.index = Index(run_on_start=run_on_start)
		self.cache = BlockCache(run_on_start=run_on_start)
		self.url_index = UrlIndex()

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


	async def get_notion_page_details(self, page_id=None, database_id=None):
		if page_id is None and database_id is None:
			page_id = self.landing_page_id

		try:
			if page_id is not None:
				page_id = self.index.to_uuid(page_id)
				# Example: check cache, etc.

			if database_id is not None:
				database_id = self.index.to_uuid(database_id)
				cache_entry = self.cache.get_database(database_id)
				if cache_entry is not None:
					return cache_entry

			url = (
				f"https://api.notion.com/v1/pages/{page_id}"
				if page_id is not None
				else f"https://api.notion.com/v1/databases/{database_id}"
			)

			# Rate limiting + shared client usage
			await AsyncClientManager.wait_for_next_request()
			client = await AsyncClientManager.get_client()
			response = await client.get(url, headers=self.headers)

			if response.status_code != 200:
				log.error(response.status_code)
				return self.clean_error_message(response.json())
			else:
				# TODO: Check modification date. Invalidate children if modified.

				data = self.convert_message(response.json(), clean_timestamps=False)

				uuid = self.index.to_uuid(data["id"])
				if uuid is None:
					self.cache.invalidate_page_if_expired(uuid, data["last_edited_time"])
					self.index.visit_uuid(uuid)

				data = self.clean_timestamps(data)

				# TODO: Add page to cache? Then when would we invalidate it?
				# TODO: Load children blocks from cache?
				# TODO: Increase visit count

				# Possibly invalidate cache, etc.
				return data

		except ValueError as e:
			log.error(e)
			return str(e)


	async def get_block_content(self, block_id, start_cursor=None):
		uuid = self.index.to_uuid(block_id)
		if uuid is None:
			return None

		cached = None

		url = f"https://api.notion.com/v1/blocks/{uuid}/children?page_size=20"
		if start_cursor is not None:
			sc_uuid = self.formatted_uuid(start_cursor)
			url += f"&start_cursor={sc_uuid}"
			cached = self.cache.get_block(sc_uuid)
		else:
			cached = self.cache.get_block(uuid)

		if cached is not None:
			return cached

		await AsyncClientManager.wait_for_next_request()
		client = await AsyncClientManager.get_client()
		response = await client.get(url, headers=self.headers)

		if response.status_code != 200:
			log.error(response.status_code)
			return self.clean_error_message(response.json())
		else:

			data = self.convert_message(response.json(), clean_type=False, clean_timestamps=False)

			for block in response.json()["results"]:
				self.cache.invalidate_block_if_expired(block["id"], block["last_edited_time"])

			data = self.clean_timestamps(data)

			children_uuids = [block["id"] for block in data["results"]]

			for uuid, content in zip(children_uuids, data["results"]):
				# TODO: Also save last_edited_time
				self.cache.add_block(uuid, content)

			self.cache.add_parent_children_relationships(
				uuid,
				children_uuids,
				parent_type=ObjectType.BLOCK,
				child_type=ObjectType.BLOCK)

			# TODO: Update or delete children-parent relationships if content of block is modified
			
			if start_cursor is None:
				self.cache.add_block(uuid, data)
			else:
				self.cache.add_block(start_cursor, data)

			return data


	async def search_notion(self, query, filter_type=None,
							start_cursor=None, sort="descending"):

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
			payload["start_cursor"] = self.formatted_uuid(start_cursor)

		await AsyncClientManager.wait_for_next_request()
		client = await AsyncClientManager.get_client()
		response = await client.post(url, headers=self.headers, json=payload)

		try:
			response_json = response.json()

			if response.status_code != 200:
				log.error(response.status_code)
				return self.clean_error_message(response_json)
			
			#log.common(response_json)
			
			log.flow("Converting message")
			data = self.convert_message(response_json, clean_timestamps=False)
			log.flow(f"Found {len(data['results'])} search results")
			data = self.clean_timestamps(data)
			return data

		except Exception as e:
			log.error(f"Error processing search response: {str(e)}")
			return {"error": str(e)}


	async def query_database(self, database_id, filter=None, start_cursor=None):
		if filter is None:
			filter = {}

		url = f"https://api.notion.com/v1/databases/{database_id}/query"
		payload = {
			"page_size": self.page_size,
		}
		if filter:
			payload["filter"] = filter
		if start_cursor is not None:
			payload["start_cursor"] = self.formatted_uuid(start_cursor)

		await AsyncClientManager.wait_for_next_request()
		client = await AsyncClientManager.get_client()
		response = await client.post(url, headers=self.headers, json=payload)

		if response.status_code != 200:
			log.error(response.status_code)
			return self.clean_error_message(response.json())
		else:
			# TODO: Invalidate blockes recursively if they are not up to date
			data = self.convert_message(response.json(), clean_timestamps=False)
			return self.clean_timestamps(data)

		# TODO: Consider storing a sorted list of often visited pages


	def set_favourite(self, uuid: int | list[int], set: bool) -> str:

		message = self.index.set_favourite_int(uuid, set)
		return message


	def _generate_notion_url(self, notion_id):
		if notion_id is None:
			return None
		
		base_url = "https://www.notion.so/"
		formatted_id = notion_id.replace("-", "")
		
		return f"{base_url}{formatted_id}"
	

	def extract_notion_id(self, url):
		if url is None:
			return None
		
		base_url = "https://www.notion.so/"
		# TODO: Strip extra content, if any
		# TODO: Strip query parameters, if any
		formatted_id = url.replace(base_url, "")
		
		return formatted_id


	def convert_message(self, message : dict | list, clean_timestamps = True, clean_type = True) -> dict | list:

		message = self.clean_response_details(message)
		message = self.convert_to_index_id(message)
		message = self.convert_urls_to_id(message)
		if clean_timestamps:
			message = self.clean_timestamps(message)
		if clean_type:
			message = self.clean_type(message)
		return message
	

	def clean_response_details(self, message):

		def clean_object(obj):

			if isinstance(obj, dict):
				for key in list(obj.keys()):
					if obj[key] is None:
						del obj[key]
					elif isinstance(obj[key], (dict, list)) and not obj[key]:
						del obj[key]
					elif key in ['icon', 'cover', 'bold', 'italic', 'strikethrough', 'underline', 'archived', 'in_trash', 'last_edited_by', 'created_by', 'annotations']:
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

		if isinstance(message, dict):
			for key, value in message.items():
				if key in ['id', 'next_cursor', 'page_id', 'database_id', 'block_id']:
					# Property ids are short, ignore them
					if self.index.converter.validate_uuid(value):
						cleaned_uuid = self.index.converter.clean_uuid(value)
						uuid = self.index.add_uuid(cleaned_uuid)
						message[key] = uuid
					else:
						# Silently ignore non-uuids
						pass
				else:
					self.convert_to_index_id(value)
		elif isinstance(message, list):
			for item in message:
				self.convert_to_index_id(item)

		return message
	

	def convert_urls_to_id(self, message):

		# TODO: Also handle internal Notions links:
		# 'plain_text': 'Metaprompt', 'href': '/1399efeb667680939950d25093855de5'}

		def convert_object(obj):
			if isinstance(obj, dict):
				for key in list(obj.keys()):
					if key in ["url", "href", "content", "plain_text"] and isinstance(obj[key], str):
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

		if "object" in message:
			del message["object"]
		if "request_id" in message:
			del message["request_id"]

		return message


	def formatted_uuid(self, uuid: str | int) -> str:
		if isinstance(uuid, int):
			uuid = self.index.get_uuid(uuid)
		return self.index.converter.to_formatted_uuid(uuid)


	def save_now(self):
		#  TODO: Move both to one class that manages storage?
		self.index.save_now()
		self.cache.save_now()


