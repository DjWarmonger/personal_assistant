from typing import Optional, Type, Any, Dict, Union, Tuple, Callable
from langchain_core.pydantic_v1 import Field, validator

from langfuse.decorators import observe
from tz_common import log, JsonConverter
from tz_common.tasks import AgentTask, AgentTaskList
from tz_common.langchain_wrappers import ContextAwareTool, AgentState, AddTaskTool, CompleteTaskTool

from operations.json_crud import JsonCrud
from operations.info import get_json_info
from operations.search_global import search_global
from operations.summarize_json import truncated_json_format
from .agentState import JsonDocumentType

json_crud = JsonCrud()
json_converter = JsonConverter()

def get_json_doc(context: AgentState, doc_type: JsonDocumentType) -> Dict[str, Any]:
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

def paginate_results(result: Any, start_index: int = 0, max_chars: int = 2000) -> Tuple[str, Optional[int]]:
	"""Helper function to paginate results.
	
	Args:
		result: The result to paginate
		start_index: Starting index in the list of items (not characters)
		max_chars: Maximum number of characters to return
		
	Returns:
		Tuple containing:
		- Paginated result string
		- Next item index if there are more results, None if no more results
	"""
	def convert_to_sorted_list(data: Any) -> list:
		"""Convert data to sorted list."""
		if isinstance(data, dict):
			return sorted([{k: v} for k, v in data.items()], key=lambda x: list(x.keys())[0])
		elif isinstance(data, (list, tuple)):
			return sorted(data)
		return [data]

	# Convert to sorted list
	sorted_result = convert_to_sorted_list(result)
	total_items = len(sorted_result)
	
	if start_index >= total_items:
		return f"Index out of bounds, {total_items} items available", None
	
	# Build output string item by item until we hit character limit
	output_parts = []
	current_chars = 0
	current_index = start_index
	
	while current_index < total_items:
		item = sorted_result[current_index]
		item_str = json_converter.remove_spaces(item)
		
		# Check if adding this item would exceed the character limit
		if current_chars + len(item_str) > max_chars:
			break
			
		output_parts.append(item_str)
		current_chars += len(item_str)
		current_index += 1
	
	paginated_result = "[" + ", ".join(output_parts) + "]"
	
	next_index = None
	if current_index < total_items:
		remaining_items = total_items - current_index
		next_index = current_index
		paginated_result += f"\n({remaining_items} more items, next index: {next_index})"
	
	return paginated_result, next_index

class JsonSearchTool(ContextAwareTool):
	name: str = "JsonSearch"
	description: str = "Search for values in a JSON document using path expressions with wildcard support. Path always starts at root level, and is equal to root if empty."

	class ArgsSchema(ContextAwareTool.ArgsSchema):
		doc_type: JsonDocumentType = Field(
			default=JsonDocumentType.CURRENT,
			description=f"Type of JSON document to search, one of ({', '.join([e.name for e in JsonDocumentType])})"
		)
		path: str = Field(..., description="Path to search for, supporting wildcards")
		start_index: int = Field(
			default=0,
			description="Starting index for pagination"
		)

	async def _run(self, context: AgentState, path: str = "", doc_type: JsonDocumentType = JsonDocumentType.CURRENT, 
				  start_index: int = 0, **kwargs: Any) -> tuple[AgentState, str]:
		log.flow(f"Searching JSON document {doc_type.value if hasattr(doc_type, 'value') else doc_type} with path: '{path}'")
		json_doc = get_json_doc(context, doc_type)
		result = json_crud.search(json_doc, path)
		
		# Store the result in context for future reference
		context["last_search_result"] = result
		
		paginated_result, _ = paginate_results(result, start_index)
		return context, paginated_result


class JsonSearchGlobalTool(ContextAwareTool):
	name: str = "JsonSearchGlobal"
	description: str = "Search for keys and values in a JSON document that match a regex pattern. Regex must be fully contained (begining and end) within a single key or value string, it CANNOT match across nested path consisting of multiple keys or indexes. Returns full paths to all matching elements."

	class ArgsSchema(ContextAwareTool.ArgsSchema):
		doc_type: JsonDocumentType = Field(
			default=JsonDocumentType.CURRENT,
			description=f"Type of JSON document to search, one of ({', '.join([e.name for e in JsonDocumentType])})"
		)
		pattern: str = Field(..., description="""Regular expression pattern to match against keys and values (e.g., 'user.*')
		<example>
		user.* - matches all keys and values starting with 'user'
		</example>
					   
		<example>
		zone.*property will match keys and values starting with 'zone' followed by 'property', but NOT match path 'zone.property' or 'zone.3.property', as 'zone' and 'property' belong to different levels of depth
		</example>
					   """)
		case_sensitive: bool = Field(
			default=False,
			description="Whether the search should be case-sensitive"
		)
		start_index: int = Field(
			default=0,
			description="Starting index for pagination"
		)

	async def _run(self, context: AgentState, pattern: str, doc_type: JsonDocumentType = JsonDocumentType.CURRENT, 
				  case_sensitive: bool = False, start_index: int = 0, **kwargs: Any) -> tuple[AgentState, str]:
		log.flow(f"Searching globally in JSON document {doc_type.value if hasattr(doc_type, 'value') else doc_type} with pattern: '{pattern}'")
		
		json_doc = get_json_doc(context, doc_type)
		
		try:
			result = search_global(json_doc, pattern, case_sensitive)

			# Format each value in the result
			for key, value in result.items():
				result[key] = truncated_json_format(value, max_depth=3, max_array_items=3, max_object_props=5)

			# Store the result in context for future reference
			context["last_global_search_result"] = result
			
			paginated_result, _ = paginate_results(result, start_index)
			return context, paginated_result
			
		except ValueError as e:
			return context, f"Error: {str(e)}"


class JsonModifyTool(ContextAwareTool):

	# TODO: Create a variant that can modify multiple paths at once, matching wildcard paths

	name: str = "JsonModify"
	description: str = f"Modify a value at a specific path in a current JSON document."

	# FIXME: Looks like arguments are passed as strings, while should be integers

	class ArgsSchema(ContextAwareTool.ArgsSchema):
		path: str = Field(..., description="Path to the value to modify (e.g., 'settings.theme')")
		value: Any = Field(..., description="New value to set at the specified path")


	async def _run(self, context: AgentState, path: str, value: Any, **kwargs: Any) -> tuple[AgentState, str]:
		log.flow(f"Modifying JSON document at path: '{path}'")

		json_doc = get_json_doc(context, JsonDocumentType.CURRENT)
		result = json_crud.modify(json_doc, path, value)

		context["json_doc"] = result

		message = f"Modified JSON document at path: '{path}' to value: {value}"

		# FIXME: Truncate result message - only return modified elements
		
		# Store the modified document in context
		#context["last_modified_doc"] = result
		
		return context, message
	
	#4. Integer values must be enforced with "lambda x: int(x)"
class JsonModifyMultipleTool(ContextAwareTool):
	name: str = "JsonModifyMultiple"
	description: str = """Modify multiple values in a JSON document at once, matching wildcard paths.
	Replacement value can be:
	1. A direct value (e.g. string, number, boolean, list, or object)
	2. A JSON string that will be parsed (e.g. "[1, 2, 3]" or "{"key": "value"}")
	3. A function string that will be evaluated for each match (e.g. "lambda x: x * 2" or "lambda x: x.title()")
	The function string must be a valid Python lambda expression using only basic operations (arithmetic, string methods, etc.)."""
	
	class ArgsSchema(ContextAwareTool.ArgsSchema):
		path: str = Field(..., description="Path to search for, supporting wildcards")
		replacement: Any | Callable[[Dict[str, Any]], Dict[str, Any]] = Field(
			..., 
			description="""Replacement value or function string to apply to each matched object.
			If providing a function, it must be a valid Python lambda expression using only basic operations.
			Important type handling notes:
			- String inputs will stay as strings (e.g., "123" remains a string, not converted to a number)
			- For numbers, pass them directly without quotes (e.g., 42 not "42")
			- To convert string to integer, use the lambda: "lambda x: int(x)"
			- To convert number to string, use the lambda: "lambda x: str(x)"
			
			Examples:
			- Direct value: Set categories: "products.*.categories" with ["electronics", "computers"]
			- Direct value: Set metadata: "products.*.metadata" with {"source": "import", "batch": 123}
			- Function: Apply 20% discount: "products.*.price" with "lambda x: round(x * 0.8, 2)"
			- Function: Format text: "products.*.name" with "lambda x: x.title()"
			- Function: Convert to string: "products.*.id" with "lambda x: str(x).zfill(3)"
			- Function: Set constant: "products.*.in_stock" with "lambda x: True"
			"""
		)

	def _evaluate_replacement(self, replacement: Any) -> Any | Callable:
		"""Evaluate replacement if it's a lambda string or JSON string, otherwise return as is."""
		if not isinstance(replacement, str):
			return replacement

		# If it's a lambda expression, evaluate it
		if replacement.strip().startswith("lambda"):
			try:
				# Try to compile the lambda first to catch syntax errors
				compile(replacement, '<string>', 'eval')
				
				replacement_func = eval(replacement)
				if not callable(replacement_func):
					raise ValueError("must be a function")
				
				return replacement_func
			except SyntaxError as e:
				raise ValueError(f"Invalid lambda expression: {str(e)}")
			except Exception as e:
				raise e

		# If it looks like a JSON array or object, try to parse it
		stripped = replacement.strip()
		if stripped.startswith(('[', '{')):
			try:
				import json
				return json.loads(replacement)
			except json.JSONDecodeError:
				return replacement

		# Return as plain string - do not convert numeric strings
		return replacement

	async def _run(self, context: AgentState, path: str, replacement: Any | Callable[[Dict[str, Any]], Dict[str, Any]], **kwargs: Any) -> tuple[AgentState, str]:
		log.flow(f"Modifying multiple JSON document at path: '{path}'")

		json_doc = get_json_doc(context, JsonDocumentType.CURRENT)
		
		# Evaluate replacement if it's a lambda string or JSON string
		evaluated_replacement = self._evaluate_replacement(replacement)

		matches = json_crud.search(json_doc, path)

		modified_count = 0
		for found_path, old_value in matches.items():
			try:
				new_value = evaluated_replacement(old_value) if callable(evaluated_replacement) else evaluated_replacement
				json_doc = json_crud.modify(json_doc, found_path, new_value)
				# Only count as modified if the value actually changed
				if new_value != old_value:
					modified_count += 1
			except Exception as e:
				raise ValueError(f"Failed to apply replacement to value '{old_value}': {str(e)}")
			
		if modified_count == 0:
			return context, "No changes were made to the JSON document, check correct path and replacement value"
			
		message = f"Modified {modified_count} of {len(matches)} matches in JSON document at path: '{path}'"

		context["json_doc"] = json_doc
		return context, message


class JsonAddTool(ContextAwareTool):
	name: str = "JsonAdd"
	description: str = "Add a new value at a specific path in a JSON document"

	class ArgsSchema(ContextAwareTool.ArgsSchema):
		path: str = Field(..., description="Path where to add the value (e.g., 'settings.notifications')")
		value: Any = Field(..., description="Value to add at the specified path")


	async def _run(self, context: AgentState, path: str, value: Any, **kwargs: Any) -> tuple[AgentState, str]:
		log.flow(f"Adding to JSON document at path: {path}")
		json_doc = get_json_doc(context, JsonDocumentType.CURRENT)
		result = json_crud.add(json_doc, path, value)
		
		# Store the modified document in context
		#context["last_added_doc"] = result
		context["json_doc"] = result
		
		return context, json_converter.remove_spaces(result)


class JsonDeleteTool(ContextAwareTool):
	# TODO: Allow wildcards?
	name: str = "JsonDelete"
	description: str = "Delete a value at a specific path in a JSON document"

	class ArgsSchema(ContextAwareTool.ArgsSchema):
		path: str = Field(..., description="Path to the value to delete (e.g., 'users.0')")


	async def _run(self, context: AgentState, path: str, **kwargs: Any) -> tuple[AgentState, str]:
		log.flow(f"Deleting from JSON document at path: {path}")
		json_doc = get_json_doc(context, JsonDocumentType.CURRENT)
		result = json_crud.delete(json_doc, path)
		
		# Store the modified document in context
		#context["last_deleted_doc"] = result
		context["json_doc"] = result
		
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
		path: str = Field(default="", description=f"Path to the object or array to get info about, starting from root.")
		doc_type: JsonDocumentType = Field(
			default=JsonDocumentType.CURRENT,
			description=f"Type of JSON document to get info from ({', '.join([e.name for e in JsonDocumentType])})"
		)

	async def _run(self, context: AgentState, path: str = "", doc_type: JsonDocumentType = JsonDocumentType.CURRENT, **kwargs: Any) -> tuple[AgentState, str]:
		log.flow(f"Getting info from {doc_type.value if hasattr(doc_type, 'value') else doc_type} JSON document at path: {path}")
		
		json_doc = get_json_doc(context, doc_type)
		log.debug(f"Retrieved JSON document of type {doc_type.value if hasattr(doc_type, 'value') else doc_type}")
		result = get_json_info(json_doc, path)
		result = truncated_json_format(result, max_depth=4, max_array_items=3, max_object_props=10)
		
		# Store the result in context for future reference
		#context["last_info_result"] = result
		# TODO: Actually present that result to agent

		message = f"Info from {doc_type.value if hasattr(doc_type, 'value') else doc_type} JSON document at path: '{path}'\n{result}"
		
		return context, message


# Set up the tools to execute them from the graph
from langgraph.prebuilt import ToolExecutor

# TODO: Implement task planning
agent_tools = [
	JsonSearchTool(),
	JsonSearchGlobalTool(),
	#JsonModifyTool(),
	JsonModifyMultipleTool(),
	JsonAddTool(),
	JsonDeleteTool(),
	#JsonLoadTool(),
	#JsonSaveTool(),
	JsonInfoTool(),
	#CompleteTaskTool()
]

tool_executor = ToolExecutor(agent_tools)

import json
import langchain_core.utils.function_calling
# Monkey patch to use our custom convert_to_openai_function
# FIXME: Try to remove it once graph works
langchain_core.utils.function_calling.convert_to_openai_function = lambda tool: tool.convert_to_openai_function() 