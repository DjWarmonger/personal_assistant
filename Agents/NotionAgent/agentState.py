from tz_common.langchain_wrappers import AgentState

class NotionAgentState(AgentState):
	
	# TODO: Make sure key is converted to int
	visitedBlocks: dict[int, str] = {}
	


# TODO: Design flow betwen agents?