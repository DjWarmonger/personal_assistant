from typing import Annotated, Sequence, Callable, Any, Awaitable
from typing_extensions import TypedDict
#from pydantic.v1 import BaseModel, Field, PrivateAttr
import asyncio

from langchain_core.messages import BaseMessage, AIMessage
from langgraph.graph.message import add_messages

from tz_common.tasks import AgentTask, AgentTaskList
from tz_common.logs import log


class AgentState(TypedDict):

	messages: Annotated[Sequence[BaseMessage], add_messages] = []

	# TODO: Should initial prompt be list or just one message?
	initialPrompt: Annotated[Sequence[BaseMessage], add_messages] = []
	unsolvedTasks: set[AgentTask] = set()
	completedTasks: set[AgentTask] = set()
	functionCalls: Annotated[Sequence[BaseMessage], add_messages] = []
	toolResults: Annotated[Sequence[BaseMessage], add_messages] = []
	recentResults: Annotated[Sequence[BaseMessage], add_messages] = []

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


# TODO: Move to separate class?
def trim_recent_results(state: AgentState, max_chars: int = 10000) -> AgentState:
	"""
	Trim recent results to stay within character limit.
	
	Args:
		state: Current graph state
		max_chars: Maximum total characters to keep
	
	Returns:
		Updated state with trimmed recentResults
	"""
	recentResults = state.get('recentResults', [])
	
	# Calculate total characters
	total_characters = sum(len(message.content) for message in recentResults)
	
	# Trim messages while exceeding max_chars
	while total_characters > max_chars and recentResults:
		message = recentResults.pop(0)
		total_characters -= len(message.content)
		log.debug(f"Popped message with length of {len(message.content)} characters")
	
	state["recentResults"] = recentResults
	return state



