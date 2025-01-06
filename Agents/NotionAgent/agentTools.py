from typing import Optional, Type

from pydantic.v1 import BaseModel, Field, validator
from langchain.tools import BaseTool
from langchain.callbacks.manager import (
	AsyncCallbackManagerForToolRun,
	CallbackManagerForToolRun,
)

from langfuse.decorators import observe
#from pydantic import BaseModel, Field

from notion_client import NotionClient
from tz_common import log, JsonConverter

client = NotionClient()
json_converter = JsonConverter()

class SearchQuery(BaseModel):

	query: str = Field(
		default="",
		description="Search query"
	)

class SearchToolSchema(BaseModel):

	query: str = Field(description="Search query")

class NotionSearchTool(BaseTool):

	name: str = "NotionSearch"
	description: str = "Search for pages, blocks or databases in Notion"
	args_schema: Type[SearchToolSchema] = SearchQuery

	def _run(
		self,
		query: str,
		run_manager: Optional[CallbackManagerForToolRun] = None,
	) -> dict:
		"""Run the tool"""
		return self.search_notion(query)
		#return {"search_results" : self.search_notion(query)}
	
	async def _arun(
		self,
		query: str,
		run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
	) -> str:
		
		log.flow(f"Searching Notion (async)... {query}")
		
		result = await client.search_notion(query)
		return json_converter.remove_spaces(result)
	
	def search_notion(
		self,
		query: str,
	) -> str:
		
		# TODO: Common logging utility for all agents

		log.flow(f"Searching Notion... {query}")
		
		return client.search_notion(query)


class DetailsTarget(BaseModel):

	notion_id: str = Field(
		default="",
		description="UUID of the page, block or database to navigate to"
	)

class DetailsToolchema(BaseModel):

	# TODO: Implement index <-> id resolution
	# index_id: int = Field(description="Index ID")
	notion_id: str = Field(description="UUID")

class NotionPageDetailsTool(BaseTool):

	name: str = "NotionPageDetails"
	description: str = "Get details of a page, block or database in Notion"
	args_schema: Type[DetailsToolchema] = DetailsTarget

	def _run(
		self,
		notion_id: str,
		run_manager: Optional[CallbackManagerForToolRun] = None,
	) -> dict:
		"""Run the tool"""
		return self.get_notion_page_details(notion_id)

	async def _arun(
		self,
		run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
		**kwargs: dict
	) -> str:
	
		notion_id = kwargs.get("notion_id")

		log.flow(f"Getting details of Notion page... {notion_id}")

		result = await client.get_notion_page_details(page_id=notion_id)
		return json_converter.remove_spaces(result)
	
	def get_notion_page_details(
		self,
		notion_id: str,
	) -> str:
		
		log.flow(f"Getting details of Notion page... {notion_id}")
		
		# TODO: Automatically recognize page / block / database
		return client.get_notion_page_details(page_id=notion_id)

class GetChildrenTarget(BaseModel):

	index: int | str= Field(
		...,
		description="index id or uuid of the page or block to retrieve children for"
	)
	start_cursor: str = Field(
		default=None,
		description='Cursor to start from, use "next_cursor" from previous response to get the next page'
	)

class GetChildrenToolSchema(BaseModel):
	pass

	# TODO: Implement index <-> id resolution
	# index_id: int = Field(description="Index ID")
	#notion_id: str = Field(description="UUID")

class NotionGetChildrenTool(BaseTool):

	name: str = "NotionGetChildren"
	description: str = "Retrieve children of a page or block in Notion"
	args_schema: Type[GetChildrenToolSchema] = GetChildrenTarget

	def _run(
		self,
		index: int | str,
		start_cursor: str = None,
		run_manager: Optional[CallbackManagerForToolRun] = None,
	) -> dict:
		"""Run the tool"""
		return self.get_block_content(index)
	async def _arun(
		self,
		index: int | str,
		start_cursor: str = None,
		run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
	) -> str:
		
		log.flow(f"Retrieving children of Notion block... {index}" + f"start cursor: {start_cursor}" if start_cursor is not None else "")
		
		# TODO: Automatically recognize page / block
		result = await client.get_block_content(block_id=index, start_cursor=start_cursor)
		return json_converter.remove_spaces(result)
	
	def get_block_content(
		self,
		index: int | str,
		start_cursor: str = None,
	) -> str:
		
		log.flow(f"Retrieving children of Notion block... {index}" + f"start cursor: {start_cursor}" if start_cursor is not None else "")
		
		# TODO: Automatically recognize page / block
		return client.get_block_content(block_id=index, start_cursor=start_cursor)


class QueryDatabaseTarget(BaseModel):

	notion_id: str = Field(
		default="",
		description="UUID the database to query"
	)
	start_cursor: str = Field(
		default=None,
		description='Cursor to start from, use "next_cursor" from previous response to get the next page'
	)
	filter: dict = Field(
		default={},
		description='Search filter to apply to the database query, in a form of JSON. Property names and types of keys need to match database fields. Example json: {"property": "Status","select": {"equals": "TODO"}}'
	)
"""
Property names and types need to match database fields. Example: {'and': [{'property': 'Done', 'checkbox': {'equals': True}}, {'or': [{'property': 'Tags', 'contains': 'A'}, {'property': 'Tags', 'contains': 'B'}]}]}"
"""

class QueryDatabaseToolSchema(BaseModel):
	pass

class NotionQueryDatabaseTool(BaseTool):

	name: str = "NotionQueryDatabase"
	description: str = "Query a database in Notion"
	args_schema: Type[QueryDatabaseToolSchema] = QueryDatabaseTarget

	def _run(
		self,
		notion_id: str,
		filter: dict = {},
		start_cursor: str = None,
		run_manager: Optional[CallbackManagerForToolRun] = None,
	) -> str:
		"""Run the tool"""
		return self.query_database(notion_id, filter, start_cursor)
	
	async def _arun(
		self,
		notion_id: str,
		filter: dict = {},
		start_cursor: str = None,
		run_manager: Optional[AsyncCallbackManagerForToolRun] = None
	) -> str:
		
		notion_id = notion_id.replace("-", "")
		log.flow(f"Querying Notion database... {notion_id}")
		log.flow("filter:", str(filter))
		
		result = await client.query_database(notion_id, filter, start_cursor)
		return json_converter.remove_spaces(result)
	
	def query_database(
		self,
		notion_id: str,
		filter: dict,
		start_cursor: str = None,
	) -> str:
		
		notion_id = notion_id.replace("-", "")
		log.flow(f"Querying Notion database... {notion_id}")
		log.flow("filter:", str(filter))
		
		return client.query_database(notion_id, filter, start_cursor)

# TODO: LLM should use numeric ids
# But it should be able to add uuid on request as well
# TODO: Also add Notion URL on request, with validation
class ChangeFavourtiesTarget(BaseModel):

	urlOrUuid: str = Field(
		...,
		description="URL or UUID of the Notion page, block or database to add or remove from favourites"
	)
	add: bool = Field(
		default=True,
		description="Whether to add (True) or remove (False) the UUID or URL from favourites"
	)
	title: str = Field(
		default="",
		description="Brief title of the page to be added to favourites"
	)

class ChangeFavourtiesSchema(BaseModel):
	pass

class ChangeFavourties(BaseTool):

	name: str = "ChangeFavourties"
	description: str = "Change status of a page in favourites"
	args_schema: Type[ChangeFavourtiesSchema] = ChangeFavourtiesTarget

	def _run(
		self,
		urlOrUuid: str,
		add: bool,
		title: str = "",
		run_manager: Optional[CallbackManagerForToolRun] = None,
	) -> str:

		return self.add_to_favourites(urlOrUuid, set, title)


	# TODO: It doesn't do anything asyncronously, is that ok?
	async def _arun(
		self,
		urlOrUuid: str,
		add: bool,
		title: str = "",
		run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
	) -> str:

		return self.add_to_favourites(urlOrUuid, set, title)
	

	def add_to_favourites(
		self,
		urlOrUuid: str,
		add: bool,
		title: str = "",
	) -> str:

		notion_id = client.index.add_notion_url_or_uuid_to_favourites(urlOrUuid, set, title)
		
		return f"Added {urlOrUuid} to favourites with id {notion_id}"


def get_link_from_id(notion_id):
	# Allow to resolve short id into full link for user convenience
	# Should also work for images and embedded files
	pass


def get_favourites():
	# TODO: Allow Agent to use this
	pass

def get_most_visited_pages(count : int = 10):
	# TODO: Allow Agent to use this
	pass

def request_human_feedback():
	# TODO: Toggle availability of this tool with flag
	pass

# Set up the tools to execute them from the graph
from langgraph.prebuilt import ToolExecutor

# Set up the agent's tools
agent_tools = [
	NotionSearchTool(),
	NotionPageDetailsTool(),
	NotionGetChildrenTool(),
	NotionQueryDatabaseTool(),
	ChangeFavourties()
	]

tool_executor = ToolExecutor(agent_tools)