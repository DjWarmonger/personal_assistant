from typing import Any, Dict, List, Tuple
from typing_extensions import NotRequired

from pydantic import Field

from tz_common.langchain_wrappers import AgentState
from operations.blockTree import BlockTree


class PlannerAgentState(AgentState):
	blockTree: NotRequired[Any]  # BlockTree field for planner state


class NotionAgentState(AgentState):
	visitedBlocks: list[tuple[int, str]] = Field(default_factory=list)
	blockTree: NotRequired[Any]  # BlockTree field for notion agent state
	
	# No need for init comments since we now explicitly declare blockTree


class WriterAgentState(AgentState):
	visitedBlocks: list[tuple[int, str]] = Field(default_factory=list)
	blockTree: NotRequired[Any]  # BlockTree field for writer agent state
	
	# No need for init comments since we now explicitly declare blockTree