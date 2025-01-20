from dotenv import load_dotenv
import os

from asyncClientManager import AsyncClientManager
from index import Index
from urlIndex import UrlIndex
from blockCache import BlockCache, ObjectType
from tz_common.logs import log, LogLevel

from utils import Utils

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
		self.landing_page_id = landing_page_id
		self.notion_token = notion_token

		self.index = Index(load_from_disk=load_from_disk, run_on_start=run_on_start)
		self.cache = BlockCache(load_from_disk=load_from_disk, run_on_start=run_on_start)
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
				data = self.convert_message(response.json(), clean_timestamps=False)

				uuid = self.index.to_uuid(data["id"])
				# FIXME: Why there is no last_edited_time in unit test?
				# FIXME: Does this happen with real pages?
				last_edited_time = data["last_edited_time"] if "last_edited_time" in data else None
				if uuid is not None:
					if last_edited_time is not None:
						self.cache.invalidate_page_if_expired(uuid, Utils.convert_date_to_timestamp(last_edited_time))
					self.index.visit_uuid(uuid)

				data = self.clean_timestamps(data)

				# TODO: Do we need to create parent-child relationships here?
				# TODO: Add page to cache? Then when would we invalidate it?

				return data

		except ValueError as e:
			log.error(e)
			return str(e)


	async def get_block_content(self, block_id, start_cursor=None):
		uuid = self.index.to_uuid(block_id)
		if uuid is None:
			return None

		cached = None
		cache_key = None

		url = f"https://api.notion.com/v1/blocks/{uuid}/children?page_size=20"
		if start_cursor is not None:
			sc_uuid = self.formatted_uuid(start_cursor)
			url += f"&start_cursor={sc_uuid}"
			cache_key = sc_uuid
		else:
			cache_key = uuid

		cached = self.cache.get_block(cache_key)

		if cached is not None:
			return cached

		await AsyncClientManager.wait_for_next_request()
		client = await AsyncClientManager.get_client()
		response = await client.get(url, headers=self.headers)

		if response.status_code != 200:
			log.error(response.status_code)
			return self.clean_error_message(response.json())
		else:

			data = self.convert_message(response.json(),
							   clean_type=False,
							   clean_timestamps=False,
							   convert_to_index_id=False)

			for block in response.json()["results"]:
				self.cache.invalidate_block_if_expired(block["id"], block["last_edited_time"])

			children_uuids = [block["id"] for block in data["results"]]

			# TODO: Batch add multiple blocks?
			for uuid, content in zip(children_uuids, data["results"]):
				# TODO: Save last_edited_time / timestamp in db?
				self.cache.add_block(uuid, content)

			# TODO: Make sure this enum works for db and page
			self.cache.add_parent_children_relationships(
				cache_key,
				children_uuids,
				parent_type=ObjectType.BLOCK,
				child_type=ObjectType.BLOCK)

			# TODO: Update or delete children-parent relationships if content of block is modified

			# TODO: Is the type relevant an this point?
			data = self.clean_type(data)
			data = self.clean_timestamps(data)
			data = self.convert_to_index_id(data)

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


		cache_entry = self.cache.get_search_results(query, filter_type, start_cursor)
		if cache_entry is not None:
			return cache_entry

		await AsyncClientManager.wait_for_next_request()
		client = await AsyncClientManager.get_client()
		response = await client.post(url, headers=self.headers, json=payload)

		try:
			response_json = response.json()

			if response.status_code != 200:
				log.error(response.status_code)
				return self.clean_error_message(response_json)
			
			cache_key = self.cache.create_search_results_cache_key(query, filter_type, start_cursor)
			
			#log.common(response_json)

			block_ids = [block["id"] for block in response_json["results"]]

			# TODO: Make sure children are actually blocks
			# TODO: Handle pages or maybe db if they are not blocks
			self.cache.add_parent_children_relationships(
				cache_key,
				block_ids,
				parent_type=ObjectType.BLOCK,
				child_type=ObjectType.BLOCK)
				# TODO: Invalidate cache is any children is modified. But not here, as we're going to add it to cache anyway.

			# Invalidate each child with last_edited_time
			for block in response_json["results"]:
				self.cache.invalidate_block_if_expired(block["id"], block["last_edited_time"])

				# TODO: Invalidate cache for all matching parent searches, not just one exact query

			log.flow("Converting message")
			data = self.convert_message(response_json)
			log.flow(f"Found {len(data['results'])} search results")

			# Max ttl for search results is 30 days
			self.cache.add_search_results(query, data, filter_type, start_cursor, ttl = 30 * 24 * 60 * 60)

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

		cache_entry = self.cache.get_database_query_results(database_id, filter, start_cursor)
		if cache_entry is not None:
			return cache_entry

		await AsyncClientManager.wait_for_next_request()
		client = await AsyncClientManager.get_client()
		response = await client.post(url, headers=self.headers, json=payload)

		if response.status_code != 200:
			log.error(response.status_code)
			return self.clean_error_message(response.json())
		else:
			# TODO: Invalidate blocks recursively if they are not up to date
			data = self.convert_message(response.json(), clean_timestamps=False, convert_to_index_id=False)

			for block in data["results"]:
				if "last_edited_time" in block:
					self.cache.invalidate_block_if_expired(block["id"], block["last_edited_time"])

			return self.convert_to_index_id(self.clean_timestamps(data))


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


	def convert_message(self,
						message : dict | list,
						clean_timestamps : bool = True,
						clean_type : bool = True,
						convert_to_index_id : bool = True,
						convert_urls : bool = True) -> dict | list:

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


