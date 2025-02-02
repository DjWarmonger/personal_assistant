from typing import Dict, Type, Any, Sequence, Tuple
from pydantic.v1 import BaseModel, Field

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
		# Automatically assign the ArgsSchema to the class

		super().__init_subclass__(**kwargs)
		if hasattr(cls, "ArgsSchema"):
			cls.args_schema = cls.ArgsSchema

	def _run(self, context: AgentState, **kwargs: Any) -> tuple[AgentState, str]:
		"""Override this method to implement tool-specific logic.
		Can be defined as async"""
		# Modify the context as needed
		context.additional_data['modified'] = True

		# Pass other objects and artifacts via context
		return context, "Tool suceeded"


	async def _arun(self, **kwargs: Any) -> Tuple[AgentState, str]:
		"""
		Async run method that handles different input formats.
		
		Args:
			context: The context object (first positional or keyword argument)
			tool_input: Additional input arguments
			**kwargs: Additional keyword arguments
		"""

		#log.debug(f"kwargs:", kwargs)

		if 'context' not in kwargs:
			raise ValueError("Context must be provided")
		else:
			context = kwargs.pop('context')
		
		# Auto-map __arg1, __arg2, etc. to the corresponding field names defined in ArgsSchema
		if hasattr(self, "ArgsSchema"):
			field_names = list(name for name in self.ArgsSchema.__fields__.keys() if name != "context")
			positional_keys = [k for k in kwargs if k.startswith("__arg")]
			# Sort positional keys based on their numeric order (e.g., __arg1, __arg2)
			sorted_keys = sorted(positional_keys, key=lambda k: int(k.replace("__arg", "")))
			for i, key in enumerate(sorted_keys):
				if i < len(field_names):
					kwargs[field_names[i]] = kwargs.pop(key)

		#log.debug(f"kwargs:", kwargs)
		
		# Call the synchronous _run method
		result = self._run(context, **kwargs)
		if asyncio.iscoroutine(result):
			result = await result
		return result

"""

# Example subclass of the custom base tool

class MyCustomTool(ContextAwareTool):
	name: str = "My Custom Tool"
	description: str = "A tool that modifies the context and accepts additional arguments."

	def _run(self, context: AgentState, **kwargs: Any) -> Any:
		# Call the parent method to modify the context
		modified_context, additional_args = super()._run(context, **kwargs)
		# Add custom logic here
		modified_context.additional_data['custom_key'] = "custom_value"
		modified_context.additional_data.update(additional_args)  # Update context with additional args
		return modified_context

# Example usage

context = AgentState(user_id="user123", session_id="session456")
tool = MyCustomTool()
result = tool.invoke({"context": context.dict(), "extra_arg1": "value1", "extra_arg2": 42})
print(result)  # Output: {'user_id': 'user123', 'session_id': 'session456', 'additional_data': {'modified': True, 'custom_key': 'custom_value', 'extra_arg1': 'value1', 'extra_arg2': 42}}

"""