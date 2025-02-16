from typing import Any

from pydantic import Field

from tz_common.langchain_wrappers import AgentState
from blockTree import BlockTree


class PlannerAgentState(AgentState):

	def __init__(self, **data: Any):
		# TODO: Remove, didn't help
		super().__init__(**data)


class NotionAgentState(AgentState):
		
	visitedBlocks: list[tuple[int, str]] = Field(default_factory=list)
	blockTree: BlockTree = BlockTree()


class WriterAgentState(AgentState):

	visitedBlocks: list[tuple[int, str]] = Field(default_factory=list)
	blockTree: BlockTree = BlockTree()