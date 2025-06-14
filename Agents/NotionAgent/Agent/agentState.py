from typing import Any, Dict, List, Tuple
from typing_extensions import NotRequired

from pydantic import Field

from tz_common.langchain_wrappers import AgentState
from operations.blocks.blockTree import BlockTree
from operations.blocks.blockDict import BlockDict


class PlannerAgentState(AgentState):
	blockTree: NotRequired[Any]  # BlockTree field for planner state


class NotionAgentState(AgentState):
	visitedBlocks: BlockDict = Field(default_factory=BlockDict)
	blockTree: NotRequired[Any]  # BlockTree field for notion agent state
	
	# No need for init comments since we now explicitly declare blockTree


class WriterAgentState(AgentState):
	visitedBlocks: BlockDict = Field(default_factory=BlockDict)
	blockTree: NotRequired[Any]  # BlockTree field for writer agent state
	
	# No need for init comments since we now explicitly declare blockTree