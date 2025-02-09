from tz_common.langchain_wrappers import AgentState

class PlannerAgentState(AgentState):
	
	pass


class NotionAgentState(AgentState):

	# TODO: Make sure key is converted to int
	visitedBlocks: dict[int, str] = {}
	

class WriterAgentState(AgentState):

	pass

# TODO: Design flow betwen agents?