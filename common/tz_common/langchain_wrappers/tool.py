from typing import Dict, Type, Any, Sequence, Tuple
from langchain_core.pydantic_v1 import BaseModel, Field
from pydantic.v1 import create_model

from langchain_core.messages import BaseMessage, AIMessage
from langchain_core.tools import BaseTool

from tz_common.tasks import AgentTask
from tz_common.langchain_wrappers import AgentState
from tz_common import log
import asyncio

# Custom base tool class
class ContextAwareTool(BaseTool):
	"""A base tool that requires a context object as input and can take additional arguments."""

	# Define the args_schema to enforce context input
	class ArgsSchema(BaseModel):
		context: AgentState


	def __init_subclass__(cls, **kwargs):
		super().__init_subclass__(**kwargs)

		if hasattr(cls, "ArgsSchema"):

			# This was verified as working
			fields: Dict[str, Any] = {}
			for name, field in cls.ArgsSchema.__fields__.items():
				if name != "context":
					# Debugging: print field name, outer_type, default and description
					#print(f"Initializing tool {cls.__name__}:", f"Adding field '{name}' - type: {field.outer_type_}, default: {field.default}, description: {field.field_info.description}")
					# Preserve the original field definition
					fields[name] = (
						field.outer_type_, 
						Field(
							default=field.default, 
							description=field.field_info.description
						)
					)

			cls.args_schema = create_model(
				f"{cls.__name__}Schema",
				**fields
			)
			"""
			cls.args_schema = create_model(
				f"{cls.__name__}Schema",
				context=(AgentState, ...),  # Make context required
				**fields
			)
			"""

			# Dump the generated schema to check names and properties:
			#print(f"Generated args_schema for {cls.__name__}:", '\n', cls.args_schema.schema_json(indent=2))
		else:
			raise ValueError(f"No ArgsSchema found for {cls.__name__}")


	@property
	def tool_call_schema(self):
		# Get the ArgsSchema defined in the subclass
		args_schema_cls = self.__class__.ArgsSchema

		# Collect fields, excluding 'context'
		tool_call_fields: Dict[str, Any] = {}
		for name, field in args_schema_cls.__fields__.items():
			if name != 'context':
				tool_call_fields[name] = (
					field.outer_type_, 
					Field(
						default=field.default, 
						description=field.field_info.description
					)
				)

		# Dynamically create a new model for tool calls
		return create_model(
			f"{self.__class__.__name__}ToolCallSchema",
			**tool_call_fields
		)


	def convert_to_openai_function(self):
		"""Custom conversion method that uses tool_call_schema"""
		return {
			"name": self.name,
			"description": self.description,
			"parameters": {
				"type": "object",
				"properties": {
					name: {
						"type": self._get_openai_type(field.type_),
						"description": field.field_info.description,
						"title": name.capitalize()
					} for name, field in self.tool_call_schema.__fields__.items()
				},
				"required": [
					name for name, field in self.tool_call_schema.__fields__.items() 
					if field.default == Ellipsis
				]
			}
		}


	def _get_openai_type(self, python_type):
		"""Convert Python types to OpenAI function types"""
		type_mapping = {
			str: "string",
			int: "integer",
			float: "number",
			bool: "boolean",
			list: "array"
		}
		return type_mapping.get(python_type, "string")



	def _run(self, context: AgentState, **kwargs: Any) -> tuple[AgentState, str]:
		"""
		Override this method to implement tool-specific logic.
		Can be defined as async

		Example implementation:

		# Modify the context as needed
		context.additional_data['modified'] = True

		# Pass other objects and artifacts via context
		return context, "Tool suceeded"
		"""

		raise NotImplementedError("Subclasses must implement _run method")


	async def _arun(self, **kwargs: Any) -> Tuple[AgentState, str]:
			"""
			Async run method that handles different input formats.
			"""
			if 'context' not in kwargs:
				raise ValueError("Context must be provided")
			
			context = kwargs.pop('context')
			
			# Call the synchronous _run method
			result = self._run(context, **kwargs)
			if asyncio.iscoroutine(result):
				result = await result
			return result