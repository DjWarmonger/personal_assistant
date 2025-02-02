from typing import Sequence, Callable, Any, Awaitable
from typing_extensions import TypedDict
#from pydantic.v1 import BaseModel, Field, PrivateAttr
import asyncio

from langchain_core.messages import BaseMessage, AIMessage

from tz_common.tasks import AgentTask, AgentTaskList


class AgentState(TypedDict):
	# Provide default empty sequences for fields that might not have initial values
	messages: Sequence[BaseMessage] = []
	initial_prompt: Sequence[BaseMessage] = []

	unsolved_tasks: set[AgentTask] = ()
	completed_tasks: set[AgentTask] = ()

	functionCalls: Sequence[BaseMessage] = []
	toolResults: Sequence[BaseMessage] = []

	recent_results: Sequence[BaseMessage] = []

	# Private async lock for protecting state modifications in async contexts
	_async_lock = asyncio.Lock()

	# Synchronous helper for state updates (if needed)
	def update_state(self, update_fn: Callable[['AgentState'], Any]) -> Any:
		# If used in both sync and async contexts, make sure not to mix the two.
		with asyncio.run_coroutine_threadsafe(self._acquire_lock_sync(), asyncio.get_event_loop()):
			# Execute the update function while under the lock
			return update_fn(self)


	async def _acquire_lock_sync(self) -> None:
		# Dummy coroutine to satisfy asyncio.run_coroutine_threadsafe requirement if needed.
		return

	# Asynchronous helper to safely update the state.
	# Pass an async function that takes the state as parameter and performs modifications.
	async def async_update_state(self, update_fn: Callable[['AgentState'], Awaitable[Any]]) -> Any:
		async with self._async_lock:
			return await update_fn(self)

	# NOTE: Developers should wrap modifications to AgentState (especially in async tasks)
	# by calling either update_state (sync) or async_update_state (async).

	# TODO: Save state to json file
	# TODO: Check if LangGraph has a way to save state to json file