from enum import Enum

from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage, AIMessage
from langfuse.decorators import observe

from tz_common.logs import log
from tz_common import create_langfuse_handler
from tz_common.langchain_wrappers import trim_recent_results, get_message_timeline_from_state, check_and_call_tools
from tz_common.tasks import AgentTaskList
from tz_common.actions import AgentActionListUtils

from .agents import notion_agent_runnable
from .agentTools import tool_executor, client
from .agentState import NotionAgentState
from operations.blockTree import BlockTree

# TODO: Add to other agents?
langfuse_handler = create_langfuse_handler(user_id="Notion Agent")


def notion_start(state: NotionAgentState) -> NotionAgentState:

	log.flow(f"Notion Agent: Entered start")

	log.debug(f"NotionAgentState:", state)

	# TODO: Add initial message to state?

	return {
		"messages": state["messages"],
		"actions": [],
		"recentResults": [],
		"visitedBlocks": {},
		"blockTree": BlockTree()
		}


def call_notion_agent(state: NotionAgentState) -> NotionAgentState:

	log.flow(f"Entered call_notion_agent")

	if "blockTree" not in state:
		raise KeyError("blockTree missing in notion state at call_notion_agent")

	state["messages"] = [msg for msg in state["messages"] if "tool_calls" not in msg.additional_kwargs]

	remaining_tasks = f"Remaining tasks:\n{str(AgentTaskList.from_list(state['unsolvedTasks']))}"
	completed_tasks = f"Completed tasks:\n{str(AgentTaskList.from_list(state['completedTasks']))}"

	tree_str = ""
	
	if not state["blockTree"].is_empty():
		tree_mapping = client.index.to_int(state["blockTree"].get_all_nodes())

		tree_names = client.index.get_names(list(tree_mapping.values()))

		log.debug(f"Tree names:", {id: name for id, name in tree_names.items() if name != ""})

		for uuid, index in tree_mapping.items():
			if index in tree_names and tree_names[index] != "":
				tree_mapping[uuid] = f"{index} : {tree_names[index]}"
			else:
				tree_mapping[uuid] = f"{index}"

		tree_str = state['blockTree'].get_tree_str(tree_mapping)

		#log.knowledge("\n\nVisited blocks:\n", tree_str)

		tree_str = f"Tree of blocks visited so far:" + '\n' + tree_str

	state = trim_recent_results(state, 2000)
	recent_calls = "Recent results of tool calls:\n"
	recent_calls += "\n\n".join([str(result.content) for result in state["recentResults"]])

	# Only append them once for this call, do not permanently add them to message history

	if state["actions"]:
		actions_str = "Actions taken:\n" + AgentActionListUtils.actions_to_string(state["actions"])

	messages_with_context = get_message_timeline_from_state(state)

	if state['unsolvedTasks']:
		messages_with_context.append(AIMessage(content=remaining_tasks))
	if state['completedTasks']:
		messages_with_context.append(AIMessage(content=completed_tasks))
	if not state["blockTree"].is_empty():
		messages_with_context.append(AIMessage(content=tree_str))
	if state["actions"]:
		messages_with_context.append(AIMessage(content=actions_str))
	if state["recentResults"]:
		messages_with_context.append(AIMessage(content=recent_calls))

	response = notion_agent_runnable.invoke({"messages": messages_with_context})

	state["messages"].append(response)
	log.debug(f"Length of messages: {len(state['messages'])}")

	return {
		"messages": state["messages"],
		"functionCalls": [],
		"recentResults": []
	}


def check_and_call_tools_wrapper(state: NotionAgentState) -> NotionAgentState:

	if "blockTree" not in state:
		raise KeyError("blockTree missing in notion state at check_and_call_tools_wrapper")

	return check_and_call_tools(state, tool_executor)


def response_check(state: NotionAgentState) -> str:

	if "blockTree" not in state:
		raise KeyError("blockTree missing in notion state at response_check")

	if state["blockTree"].is_empty():
		log.error("blockTree is empty in notion state at response_check")

	log.knowledge(f"Unsolved tasks:", "\n".join([str(task) for task in state['unsolvedTasks']]))
	log.knowledge(f"Completed tasks:", "\n".join([str(task) for task in state['completedTasks']]))

	if len(state["unsolvedTasks"]) == 0:
		for task in state["completedTasks"]:
			if task.status == "failed":
				log.error(f"Task failed: {task.name}")
				return "failed"

		log.flow(f"All tasks completed")
		return "completed"

	# TODO: handle human feedback tool
	# TODO: Handle agent question tool
	else:
		return "continue"
	

def clean_output(state: NotionAgentState):

	# This is an extra node from which we can exit the graph and return the result

	for msg in state["messages"]:
		msg.content = client.url_index.replace_placeholders(msg.content)

	return {"messages": state["messages"]}


graph = StateGraph(NotionAgentState)

graph.set_entry_point("notionAgentStart")

graph.add_node("notionAgentStart", notion_start)
graph.add_node("callNotionAgent", call_notion_agent)
graph.add_node("checkNotionTools", check_and_call_tools_wrapper)
graph.add_node("notionResponseCheck", clean_output)

graph.add_edge("notionAgentStart", "callNotionAgent")
graph.add_edge("callNotionAgent", "checkNotionTools")
graph.add_edge("checkNotionTools", "notionResponseCheck")

graph.add_conditional_edges(
	"notionResponseCheck",
	response_check,
	{
		"completed": END,
		"failed": END,
		"human_feedback_needed": END,
		"agent_question": END,
		"continue": "callNotionAgent"
	}
)

notion_agent = graph.compile()