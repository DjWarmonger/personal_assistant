from typing import TypedDict, Sequence, Set, Optional, List
from typing_extensions import TypedDict,NotRequired
import asyncio

from pydantic.v1 import BaseModel, Field
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

from tz_common.tasks import AgentTask, AgentTaskList
from tz_common.actions import AgentAction
from tz_common.logs import log


class AgentState(TypedDict):
	
	# TODO: Add agent name here? Or there's a better place?

	messages: Sequence[BaseMessage]
	initialPrompt: Sequence[BaseMessage]
	unsolvedTasks: Sequence[AgentTask]
	completedTasks: Sequence[AgentTask]
	actions: List[AgentAction]  # Changed to List for mutable operations
	toolResults: Sequence[BaseMessage]
	recentResults: Sequence[BaseMessage]

# TODO: Migrate to Pydantic v2:
"""
class AgentState(BaseModel):
    unsolvedTasks: Set[AgentTask] = set()
    completedTasks: Set[AgentTask] = set()
    # …

    @field_serializer('unsolvedTasks', 'completedTasks')
    def _set_to_list(self, v, _info):
        return [t.dict(exclude_none=True) for t in v]
"""


def create_agent_state() -> AgentState:
	"""Create a new AgentState with default values"""
	return {
		"messages": [],
		"initialPrompt": [],
		"unsolvedTasks": [],
		"completedTasks": [],
		"actions": [],
		"toolResults": [],
		"recentResults": []
	}


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
	while total_characters > max_chars and len(recentResults) > 1:
		# Do not pop last message even if its too long
		message = recentResults.pop(0)
		total_characters -= len(message.content)
		log.debug(f"Popped message with length of {len(message.content)} characters")
	
	state["recentResults"] = recentResults
	return state



