from typing import Optional, Type, Any, Dict, Union
from langchain_core.pydantic_v1 import Field, validator

from langfuse.decorators import observe
from tz_common import log, JsonConverter
from tz_common.tasks import AgentTask, AgentTaskList
from tz_common.langchain_wrappers import ContextAwareTool, AgentState, AddTaskTool, CompleteTaskTool

from operations.json_crud import JsonCrud
from operations.info import get_json_info
from .agentState import JsonDocumentType

json_crud = JsonCrud()
json_converter = JsonConverter()

"""
class RespondTool(ContextAwareTool):
	# TODO: Move to common
	name: str = "Respond"
	description: str = "Respond to the user with a message"

	class ArgsSchema(ContextAwareTool.ArgsSchema):
		message: str = Field(..., description="Message to respond with")
		# TODO: Return any artifacts?

	async def _run(self, context: AgentState, message: str, **kwargs: Any) -> tuple[AgentState, str]:
		ret = (f"Responding to the user with message: {message}")
		# TODO: Actually save the response somewhere and check for it in the graph
		context["user_response"] = message
		return context, ret
"""


class JsonSearchTool(ContextAwareTool):
	name: str = "JsonSearch"
	description: str = "Search for values in a JSON document using path expressions with wildcard support"

	class ArgsSchema(ContextAwareTool.ArgsSchema):
		json_doc: Dict[str, Any] = Field(..., description="JSON document to search in")
		path: str = Field(..., description="Path to search for, supporting wildcards (e.g., 'users.*.name')")


	async def _run(self, context: AgentState, json_doc: Dict[str, Any], path: str, **kwargs: Any) -> tuple[AgentState, str]:
		log.flow(f"Searching JSON document with path: {path}")
		result = json_crud.search(json_doc, path)
		
		# Store the result in context for future reference
		context["last_search_result"] = result
		
		return context, json_converter.remove_spaces(result)


class JsonModifyTool(ContextAwareTool):
	name: str = "JsonModify"
	description: str = f"Modify a value at a specific path in a JSON document."

	class ArgsSchema(ContextAwareTool.ArgsSchema):
		json_doc: Dict[str, Any] = Field(..., description="JSON document to modify")
		path: str = Field(..., description="Path to the value to modify (e.g., 'settings.theme')")
		value: Any = Field(..., description="New value to set at the specified path")


	async def _run(self, context: AgentState, json_doc: Dict[str, Any], path: str, value: Any, **kwargs: Any) -> tuple[AgentState, str]:
		log.flow(f"Modifying JSON document at path: {path}")
		result = json_crud.modify(json_doc, path, value)
		
		# Store the modified document in context
		context["last_modified_doc"] = result
		
		return context, json_converter.remove_spaces(result)


class JsonAddTool(ContextAwareTool):
	name: str = "JsonAdd"
	description: str = "Add a new value at a specific path in a JSON document"

	class ArgsSchema(ContextAwareTool.ArgsSchema):
		json_doc: Dict[str, Any] = Field(..., description="JSON document to add to")
		path: str = Field(..., description="Path where to add the value (e.g., 'settings.notifications')")
		value: Any = Field(..., description="Value to add at the specified path")


	async def _run(self, context: AgentState, json_doc: Dict[str, Any], path: str, value: Any, **kwargs: Any) -> tuple[AgentState, str]:
		log.flow(f"Adding to JSON document at path: {path}")
		result = json_crud.add(json_doc, path, value)
		
		# Store the modified document in context
		context["last_added_doc"] = result
		
		return context, json_converter.remove_spaces(result)


class JsonDeleteTool(ContextAwareTool):
	name: str = "JsonDelete"
	description: str = "Delete a value at a specific path in a JSON document"

	class ArgsSchema(ContextAwareTool.ArgsSchema):
		json_doc: Dict[str, Any] = Field(..., description="JSON document to delete from")
		path: str = Field(..., description="Path to the value to delete (e.g., 'users.0')")


	async def _run(self, context: AgentState, json_doc: Dict[str, Any], path: str, **kwargs: Any) -> tuple[AgentState, str]:
		log.flow(f"Deleting from JSON document at path: {path}")
		result = json_crud.delete(json_doc, path)
		
		# Store the modified document in context
		context["last_deleted_doc"] = result
		
		return context, json_converter.remove_spaces(result)


class JsonLoadTool(ContextAwareTool):
	name: str = "JsonLoad"
	description: str = "Load a JSON document from a string"

	class ArgsSchema(ContextAwareTool.ArgsSchema):
		json_string: str = Field(..., description="JSON string to parse")


	async def _run(self, context: AgentState, json_string: str, **kwargs: Any) -> tuple[AgentState, str]:
		log.flow("Loading JSON document from string")
		import json
		
		try:
			result = json.loads(json_string)
			# Store the loaded document in context
			context["loaded_json_doc"] = result
			return context, f"Successfully loaded JSON document with {len(result.keys() if isinstance(result, dict) else result)} root elements"
		except json.JSONDecodeError as e:
			return context, f"Error loading JSON: {str(e)}"


class JsonSaveTool(ContextAwareTool):
	name: str = "JsonSave"
	description: str = "Convert a JSON document to a formatted string"

	class ArgsSchema(ContextAwareTool.ArgsSchema):
		json_doc: Dict[str, Any] = Field(..., description="JSON document to convert to string")
		indent: int = Field(2, description="Number of spaces for indentation in the output string")


	async def _run(self, context: AgentState, json_doc: Dict[str, Any], indent: int = 2, **kwargs: Any) -> tuple[AgentState, str]:
		log.flow("Converting JSON document to string")
		import json
		
		try:
			result = json.dumps(json_doc, indent=indent)
			return context, result
		except Exception as e:
			return context, f"Error converting JSON to string: {str(e)}"


class JsonInfoTool(ContextAwareTool):
	name: str = "JsonInfo"
	description: str = "Get information about an object or array at a specific path in a JSON document"

	class ArgsSchema(ContextAwareTool.ArgsSchema):
		path: str = Field(default="", description=f"Path to the object or array to get info about.")
		doc_type: JsonDocumentType = Field(
			default=JsonDocumentType.CURRENT,
			description=f"Type of JSON document to get info from ({', '.join([e.name for e in JsonDocumentType])})"
		)


	def _get_json_doc(self, context: AgentState, doc_type: JsonDocumentType) -> Dict[str, Any]:
		"""Get JSON document based on the specified type."""
		doc_type_str = doc_type.name if hasattr(doc_type, 'name') else str(doc_type).upper()
		
		if doc_type_str == JsonDocumentType.INITIAL.name:
			return context["initial_json_doc"]
		elif doc_type_str == JsonDocumentType.CURRENT.name:
			return context["json_doc"]
		elif doc_type_str == JsonDocumentType.FINAL.name:
			return context["final_json_doc"]
		else:
			raise ValueError(f"Invalid JSON document type: {doc_type}")


	async def _run(self, context: AgentState, path: str = "", doc_type: JsonDocumentType = JsonDocumentType.CURRENT, **kwargs: Any) -> tuple[AgentState, str]:
		log.flow(f"Getting info from {doc_type.value if hasattr(doc_type, 'value') else doc_type} JSON document at path: {path}")
		
		json_doc = self._get_json_doc(context, doc_type)
		log.debug(f"Retrieved JSON document of type {doc_type.value if hasattr(doc_type, 'value') else doc_type}")
		result = get_json_info(json_doc, path)
		
		# Store the result in context for future reference
		#context["last_info_result"] = result
		# TODO: Actually present that result to agent

		message = f"Info from {doc_type.value if hasattr(doc_type, 'value') else doc_type} JSON document at path: {path}\n{result}"
		
		return context, message


# Set up the tools to execute them from the graph
from langgraph.prebuilt import ToolExecutor

# TODO: Implement task planning
agent_tools = [
	JsonSearchTool(),
	JsonModifyTool(),
	JsonAddTool(),
	JsonDeleteTool(),
	JsonLoadTool(),
	JsonSaveTool(),
	JsonInfoTool(),
	#RespondTool(),
	#CompleteTaskTool()
]

tool_executor = ToolExecutor(agent_tools)

import json
import langchain_core.utils.function_calling
# Monkey patch to use our custom convert_to_openai_function
# FIXME: Try to remove it once graph works
langchain_core.utils.function_calling.convert_to_openai_function = lambda tool: tool.convert_to_openai_function() 