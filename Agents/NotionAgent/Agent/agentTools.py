from typing import Optional, Type, Any
from langchain_core.pydantic_v1 import Field, validator

from langfuse.decorators import observe
from operations.notion_client import NotionClient
from operations.blockDict import BlockDict
from tz_common import log, JsonConverter
from tz_common import CustomUUID
from tz_common.tasks import AgentTask, AgentTaskList
from tz_common.langchain_wrappers import ContextAwareTool, AgentState, AddTaskTool, CompleteTaskTool, CompleteTaskWithDataTool

client = NotionClient()
json_converter = JsonConverter()


class NotionSearchTool(ContextAwareTool):
	name: str = "NotionSearch"
	description: str = "Search for pages, blocks or databases in Notion"

	class ArgsSchema(ContextAwareTool.ArgsSchema):
		query: str = Field(..., description="Search query")


	async def _run(self, context: AgentState, query: str, **kwargs: Any) -> tuple[AgentState, str]:
		log.flow(f"Searching Notion... {query}")
		result = await client.search_notion(query)
		
		# Handle new BlockDict return type or error string
		if isinstance(result, BlockDict):
			result_to_return = result.to_dict()
		elif isinstance(result, str):
			# Handle error string
			log.error(f"Error searching Notion: {result}")
			result_to_return = {"error": result}
		else:
			# Handle other return types (fallback)
			result_to_return = result
		
		return context, json_converter.remove_spaces(result_to_return)


class NotionPageDetailsTool(ContextAwareTool):
	name: str = "NotionPageDetails"
	description: str = "Get details of a page, block or database in Notion"

	class ArgsSchema(ContextAwareTool.ArgsSchema):
		notion_id: str = Field(..., description="UUID of the page, block or database to navigate to")


	async def _run(self, context: AgentState, notion_id: str, **kwargs: Any) -> tuple[AgentState, str]:
		log.flow(f"Getting details of Notion page... {notion_id}")
		result = await client.get_notion_page_details(page_id=notion_id)

		index = client.index.resolve_to_int(notion_id)

		if index is None:
			raise ValueError(f"Invalid page index: {notion_id}")
		
		visited_dict = dict(context["visitedBlocks"])
		
		# Handle new BlockDict return type or error string
		if isinstance(result, BlockDict):
			# For page details, we may have a single item in BlockDict
			result_dict = result.to_dict()
			if result_dict:
				# Use the first (and likely only) item's content
				first_key = next(iter(result_dict.keys()))
				visited_dict[index] = result_dict[first_key]
			result_to_return = result_dict
		elif isinstance(result, str):
			# Handle error string
			log.error(f"Error getting page details: {result}")
			visited_dict[index] = {"error": result}
			result_to_return = {"error": result}
		else:
			# Handle other return types (fallback)
			visited_dict[index] = result
			result_to_return = result
		
		context["visitedBlocks"] = list(visited_dict.items())

		return context, json_converter.remove_spaces(result_to_return)


class NotionGetChildrenTool(ContextAwareTool):
	name: str = "NotionGetChildren"
	description: str = "Retrieve children of a page or block in Notion. Only call if node's 'has_children' is True"

	class ArgsSchema(ContextAwareTool.ArgsSchema):
		index: int | str = Field(..., description="Index id or uuid of the page or block to retrieve children for")
		start_cursor: Optional[str] = Field(None, description='Cursor to start from, use "next_cursor" from previous response to get the next page')


	async def _run(self, context: AgentState, index: int | str, start_cursor: Optional[str] = None, **kwargs: Any) -> tuple[AgentState, str]:
		cursor_info = f" start cursor: {start_cursor}" if start_cursor is not None else ""
		log.flow(f"Retrieving children of Notion block... {index}{cursor_info}")

		block_id = client.index.resolve_to_uuid(index)

		result = await client.get_block_content(block_id=block_id, start_cursor=start_cursor, get_children=True, block_tree=context.get("blockTree"))

		visited_dict = dict(context["visitedBlocks"])

		# Handle new BlockDict return type or error string
		if isinstance(result, BlockDict):
			for block_id, content in result.items():
				visited_dict[int(block_id)] = content
			# Convert BlockDict to regular dict for JSON serialization
			result_to_return = result.to_dict()
		elif isinstance(result, dict):
			# Handle regular dict (fallback for other methods)
			for block_id, content in result.items():
				visited_dict[int(block_id)] = content
			result_to_return = result
		elif isinstance(result, str):
			# Handle error string
			log.error(f"Error getting children: {result}")
			result_to_return = {"error": result}
		else:
			# Handle other return types
			index = client.index.to_int(block_id)	
			if index is not None:
				visited_dict[index] = result
			else:
				log.error(f"Could not resolve index {block_id} to int")
			result_to_return = result

		context["visitedBlocks"] = list(visited_dict.items())

		return context, json_converter.remove_spaces(result_to_return)


class NotionGetBlockContentTool(ContextAwareTool):
	name: str = "NotionGetBlockContent"
	description: str = "Retrieve content of a page or block in Notion, recursively"


	class ArgsSchema(ContextAwareTool.ArgsSchema):
		index: int | str = Field(..., description="Index id or uuid of the page or block to retrieve content for")
		start_cursor: Optional[str] = Field(None, description='Cursor to start from, use "next_cursor" from previous response to get the next page')


	async def _run(self, context: AgentState, index: int | str, start_cursor: Optional[str] = None, **kwargs: Any) -> tuple[AgentState, str]:
		cursor_info = f" start cursor: {start_cursor}" if start_cursor is not None else ""
		log.flow(f"Retrieving content of Notion block... {index}{cursor_info}")
		
		result = await client.get_block_content(get_children=False,
							block_id=index,
							start_cursor=start_cursor,
							block_tree=context.get("blockTree"))
		
		if isinstance(index, str):
			try:
				index = int(index)
			except ValueError:
				index = client.index.to_int(index)
				if index is None:
					raise ValueError(f"Invalid block index: {index}")

		visited_dict = dict(context["visitedBlocks"])
		
		# Handle new BlockDict return type or error string  
		if isinstance(result, BlockDict):
			# Convert BlockDict to regular dict for JSON serialization
			visited_dict[index] = result.to_dict()
			result_to_return = result.to_dict()
		elif isinstance(result, str):
			# Handle error string
			log.error(f"Error getting block content: {result}")
			result_to_return = {"error": result}
		else:
			# Handle regular dict or other return types
			visited_dict[index] = result
			result_to_return = result
		
		context["visitedBlocks"] = list(visited_dict.items())

		return context, json_converter.remove_spaces(result_to_return)


class NotionQueryDatabaseTool(ContextAwareTool):
	name: str = "NotionQueryDatabase"
	description: str = "Query a database in Notion"

	class ArgsSchema(ContextAwareTool.ArgsSchema):
		notion_id: str = Field(..., description="UUID of the database to query")
		# TODO: detailed filter description for 4.1-mini
		filter: dict = Field(default={}, description='Search filter to apply to the database query. Example: {"property": "Status", "select": {"equals": "TODO"}}')
		start_cursor: Optional[str] = Field(None, description='Cursor to start from, use "next_cursor" from previous response to get the next page')


	async def _run(self, context: AgentState, notion_id: str, filter: dict = {}, start_cursor: Optional[str] = None, **kwargs: Any) -> tuple[AgentState, str]:

		notion_id = CustomUUID(value=notion_id)
		log.flow(f"Querying Notion database... {notion_id}")
		log.debug("Start cursor: ", start_cursor)
		log.debug("filter:", str(filter))
		result = await client.query_database(notion_id, filter, start_cursor)
		
		# Handle new BlockDict return type or error string
		if isinstance(result, BlockDict):
			result_to_return = result.to_dict()
		elif isinstance(result, str):
			# Handle error string
			log.error(f"Error querying database: {result}")
			result_to_return = {"error": result}
		else:
			# Handle other return types (fallback)
			result_to_return = result
		
		return context, json_converter.remove_spaces(result_to_return)


class ChangeFavourties(ContextAwareTool):
	name: str = "ChangeFavourties"
	description: str = "Change status of a page in favourites"

	class ArgsSchema(ContextAwareTool.ArgsSchema):
		urlOrUuid: str = Field(..., description="URL or UUID of the Notion page, block or database to add or remove from favourites")
		add: bool = Field(default=True, description="Whether to add (True) or remove (False) the URL/UUID from favourites")
		title: str = Field(default="", description="Brief title of the page to be added to favourites")


	async def _run(self, context: AgentState, urlOrUuid: str, add: bool, title: str = "", **kwargs: Any) -> tuple[AgentState, str]:
		notion_id = client.index.add_notion_url_or_uuid_to_favourites(urlOrUuid, add, title)
		result = f"Added {urlOrUuid} to favourites with id {notion_id}"
		return context, result


class SetTaskListTool(ContextAwareTool):

	# FIXME: Apparently 4o-mini can't pull this off

	# TODO: Move to common lib

	name: str = "SetTaskList"
	description: str = "Set the task list for the current agent, replacing the existing task list"

	class ArgsSchema(ContextAwareTool.ArgsSchema):
		task_list: AgentTaskList = Field(..., description="List of AgentTask objects to replace current tasks")


	async def _run(self, context: AgentState, task_list: AgentTaskList, **kwargs: Any) -> tuple[AgentState, str]:

		# FIXME: Must be formatted as TaskList. Else, add tasks one by one.

		log.debug("Task list:", task_list)

		# TODO: What about already solved tasks? Erase them, overwrite?
		context["unsolved_tasks"] = set(task_list)
		return context, "Task list set"



# Stub functions for additional functionality
def get_link_from_id(notion_id):

	log.flow(f"Resolving link for notion_id {notion_id}")
	# Allow to resolve short id into full link for user convenience
	pass

def get_favourites():
	# TODO: Allow Agent to use this functionality
	pass

def get_most_visited_pages(count: int = 10):
	# TODO: Allow Agent to use this functionality
	pass

def request_human_feedback():
	# TODO: Toggle availability of this tool with flag
	pass

# Set up the tools to execute them from the graph
from langgraph.prebuilt import ToolExecutor

# TODO: Move "change favourites" to planner only?

agent_tools = [
	NotionSearchTool(),
	NotionPageDetailsTool(),
	NotionGetBlockContentTool(),
	NotionGetChildrenTool(),
	NotionQueryDatabaseTool(),
	ChangeFavourties(),
	CompleteTaskTool()
	]
planner_tools = [AddTaskTool()] + agent_tools

# TODO: Allow writer to give feedback or request clarification
writer_tools = [CompleteTaskWithDataTool()]


planner_tool_executor = ToolExecutor(planner_tools)
tool_executor = ToolExecutor(agent_tools)
writer_tool_executor = ToolExecutor(writer_tools)

import json
import langchain_core.utils.function_calling
# Monkey patch to use our custom convert_to_openai_function
# FIXME: Try to remove it once graph works
langchain_core.utils.function_calling.convert_to_openai_function = lambda tool: tool.convert_to_openai_function()

"""
for tool in agent_tools:

	print("Tool call schema:")
	print(tool.tool_call_schema.schema())

	openai_function = langchain_core.utils.function_calling.convert_to_openai_function(tool)
	print("OpenAI Function Schema:")
	print(json.dumps(openai_function, indent=2))
"""
