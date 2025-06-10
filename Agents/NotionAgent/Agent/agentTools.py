from typing import Optional, Type, Any
from langchain_core.pydantic_v1 import Field, validator

from langfuse.decorators import observe
from operations.notion_client import NotionClient
from operations.blockDict import BlockDict
from operations.blockHolder import FilteringOptions
from tz_common import log, JsonConverter
from tz_common import CustomUUID
from tz_common.tasks import AgentTask, AgentTaskList
from tz_common.langchain_wrappers import ContextAwareTool, AgentState, AddTaskTool, CompleteTaskTool, CompleteTaskWithDataTool

client = NotionClient()
json_converter = JsonConverter()


def handle_client_response(result, context: AgentState, operation_name: str, 
						  add_to_visited: bool = True, visited_block_id: Optional[int] = None) -> str:
	"""
	Helper function to handle client responses consistently across all tools.
	
	Args:
		result: The result from a NotionClient method (BlockDict, str, or dict)
		context: The agent state context
		operation_name: Name of the operation for error logging
		add_to_visited: Whether to add blocks to visitedBlocks context
		visited_block_id: Specific block ID to use when adding single block to visited
		
	Returns:
		JSON string representation of the result
		
	Raises:
		Exception: If result is an error string
		TypeError: If result is an unexpected type
	"""
	# Handle error strings first
	if isinstance(result, str):
		log.error(f"Error in {operation_name}: {result}")
		raise Exception(result)
	
	# Convert all result types to BlockDict
	block_dict = BlockDict()
	
	if isinstance(result, BlockDict):
		# Already a BlockDict, use as-is
		block_dict = result
	elif isinstance(result, dict):
		# Convert regular dict to BlockDict
		for block_id, content in result.items():
			block_dict.add_block(int(block_id), content)
	else:
		log.error(f"Unexpected type of client response: {type(result)}", str(result))
		raise TypeError(f"Unexpected type: {type(result)}")
	
	# Apply filtering to all blocks in the BlockDict once
	filtered_result_dict = {}
	for block_id, content in block_dict.items():
		# Apply AGENT_OPTIMIZED filtering to each block
		filtered_content = client.block_holder.apply_filters(content.copy(), [FilteringOptions.AGENT_OPTIMIZED])
		filtered_result_dict[block_id] = filtered_content
	
	# Add to visited blocks if requested
	if add_to_visited:
		if visited_block_id is not None:
			# Add single block with specific ID (for page details)
			if filtered_result_dict:
				first_key = next(iter(filtered_result_dict.keys()))
				context["visitedBlocks"].add_block(visited_block_id, filtered_result_dict[first_key])
		else:
			# Add all blocks from result to visitedBlocks
			for block_id, content in filtered_result_dict.items():
				context["visitedBlocks"].add_block(int(block_id), content)
	
	return json_converter.remove_spaces(filtered_result_dict)


class NotionSearchTool(ContextAwareTool):
	name: str = "NotionSearch"
	description: str = "Search for pages, blocks or databases in Notion"

	class ArgsSchema(ContextAwareTool.ArgsSchema):
		query: str = Field(..., description="Search query")


	async def _run(self, context: AgentState, query: str, **kwargs: Any) -> tuple[AgentState, str]:
		log.flow(f"Searching Notion... {query}")
		result = await client.search_notion(query)
		
		return context, handle_client_response(result, context, "search_notion", add_to_visited=False)


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
		
		# Increase visit count for directly accessed page/database
		client.index.visit_int(index)
		
		return context, handle_client_response(result, context, "get_notion_page_details", visited_block_id=index)


class NotionGetBlockContentTool(ContextAwareTool):
	name: str = "NotionGetBlockContent"
	description: str = "Retrieve content of a page or block in Notion, recursively including all children"


	class ArgsSchema(ContextAwareTool.ArgsSchema):
		index: int | str = Field(..., description="Index id or uuid of the page or block to retrieve content for")
		start_cursor: Optional[str] = Field(None, description='Cursor to start from, use "next_cursor" from previous response to get the next page')


	async def _run(self, context: AgentState, index: int | str, start_cursor: Optional[str] = None, **kwargs: Any) -> tuple[AgentState, str]:
		cursor_info = f" start cursor: {start_cursor}" if start_cursor is not None else ""
		log.flow(f"Retrieving content of Notion block... {index}{cursor_info}")
		
		block_id = client.index.resolve_to_uuid(index)
		
		if block_id is None:
			error_msg = f"Could not resolve index {index} to UUID. Index may not exist in the index."
			log.error(error_msg)
			raise ValueError(error_msg)
		
		# Increase visit count for directly accessed block
		int_id = client.index.resolve_to_int(index)
		if int_id is not None:
			client.index.visit_int(int_id)
		
		result = await client.get_block_content(block_id=block_id,
							start_cursor=start_cursor,
							block_tree=context.get("blockTree"))

		return context, handle_client_response(result, context, "get_block_content")


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
		
		# Increase visit count for directly queried database
		int_id = client.index.resolve_to_int(notion_id)
		if int_id is not None:
			client.index.visit_int(int_id)
		
		result = await client.query_database(notion_id, filter, start_cursor)
		
		return context, handle_client_response(result, context, "query_database", add_to_visited=False)


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
