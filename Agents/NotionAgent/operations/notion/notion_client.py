from dotenv import load_dotenv
import os
from typing import Optional, Union

from tz_common import CustomUUID
from tz_common.logs import log, LogLevel

from .asyncClientManager import AsyncClientManager
from ..blocks.index import Index
from ..urlIndex import UrlIndex
from ..blocks.blockCache import BlockCache
from ..blocks.blockTree import BlockTree
from ..blocks.blockHolder import BlockHolder
from ..blocks.blockDict import BlockDict
from ..blocks.blockManager import BlockManager
from ..blocks.cacheOrchestrator import CacheOrchestrator
from .notionAPIClient import NotionAPIClient
from .notionService import NotionService

load_dotenv()
log.set_log_level(LogLevel.FLOW)

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_LANDING_PAGE_ID = os.getenv("NOTION_LANDING_PAGE_ID")

class NotionClient:
	"""
	Facade for Notion operations that delegates to NotionService.
	Maintains backward compatibility while using the new service architecture.
	"""

	def __init__(self,
				 notion_token=NOTION_TOKEN,
				 landing_page_id=NOTION_LANDING_PAGE_ID,
				 load_from_disk=True,
				 run_on_start=True):
		
		raw_landing_page_id = landing_page_id
		if raw_landing_page_id:
			self.landing_page_id = CustomUUID.from_string(raw_landing_page_id)
		else:
			self.landing_page_id = None
		
		self.notion_token = notion_token

		# Initialize core components
		self.index = Index(load_from_disk=load_from_disk, run_on_start=run_on_start)
		self.cache = BlockCache(load_from_disk=load_from_disk, run_on_start=run_on_start)
		self.url_index = UrlIndex()
		self.block_holder = BlockHolder(self.url_index)
		self.block_manager = BlockManager(self.index, self.cache, self.block_holder)
		
		# Initialize service layer components
		self.api_client = NotionAPIClient(self.notion_token, self.block_holder)
		self.cache_orchestrator = CacheOrchestrator(self.cache, self.block_manager, self.index)
		
		# Initialize the main service
		self.service = NotionService(
			api_client=self.api_client,
			cache_orchestrator=self.cache_orchestrator,
			index=self.index,
			url_index=self.url_index,
			block_holder=self.block_holder,
			block_manager=self.block_manager,
			landing_page_id=self.landing_page_id
		)

	async def __aenter__(self):
		await AsyncClientManager.initialize()
		return self

	async def __aexit__(self, exc_type, exc_val, exc_tb):
		# Do not close the manager; it's shared globally.
		pass


	async def get_notion_page_details(self, page_id: Optional[Union[str, CustomUUID]] = None, database_id: Optional[Union[str, CustomUUID]] = None) -> Union[BlockDict, str]:
		"""
		Facade method that delegates to NotionService.
		Maintains backward compatibility by converting exceptions to error strings.
		"""
		try:
			return await self.service.get_notion_page_details(page_id=page_id, database_id=database_id)
		except Exception as e:
			log.error(f"Error in get_notion_page_details: {e}")
			return str(e)
		

	async def get_block_content(self,
							 block_id: Union[int, str, CustomUUID],
							 start_cursor: Optional[Union[int, str, CustomUUID]] = None,
							 block_tree: Optional[BlockTree] = None) -> Union[BlockDict, str]:
		"""
		Facade method that delegates to NotionService.
		Always returns all children recursively.
		"""
		try:
			return await self.service.get_block_content(
				block_id=block_id,
				start_cursor=start_cursor,
				block_tree=block_tree
			)
		except Exception as e:
			log.error(f"Error in get_block_content: {e}")
			return str(e)
		

	async def search_notion(self, query, filter_type=None,
							start_cursor: Optional[Union[str, CustomUUID]] = None, sort="descending") -> Union[BlockDict, str]:
		"""
		Facade method that delegates to NotionService.
		"""
		try:
			return await self.service.search_notion(
				query=query,
				filter_type=filter_type,
				start_cursor=start_cursor,
				sort=sort
			)
		except Exception as e:
			log.error(f"Error in search_notion: {e}")
			return str(e)


	async def query_database(self, database_id: Union[str, CustomUUID], filter=None, start_cursor: Optional[Union[str, CustomUUID]] = None) -> Union[BlockDict, str]:
		"""
		Facade method that delegates to NotionService.
		"""
		try:
			# Parse filter using the API client's method for backward compatibility
			filter_obj = self.api_client.parse_filter(filter)
			return await self.service.query_database(
				database_id=database_id,
				filter_obj=filter_obj,
				start_cursor=start_cursor
			)
		except Exception as e:
			log.error(f"Error in query_database: {e}")
			return str(e)



