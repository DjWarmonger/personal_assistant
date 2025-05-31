from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage, AIMessage
from langfuse.decorators import observe

from tz_common.logs import log
from tz_common import create_langfuse_handler
from tz_common.langchain_wrappers import AgentState, trim_recent_results, get_message_timeline_from_state, check_and_call_tools
from tz_common.langchain_wrappers.message import create_current_time_message
from tz_common.tasks import AgentTaskList
from tz_common.actions import AgentActionListUtils

from .agents import writer_agent_runnable
from .agentTools import writer_tool_executor, client
from .agentState import WriterAgentState
from operations.blockTree import BlockTree

def writer_start(state: WriterAgentState) -> WriterAgentState:

	log.flow(f"Entered start")

	return {
		"messages": state["messages"],
		"actions": [],
		"recentResults": []
	}


def call_writer_agent(state: WriterAgentState) -> WriterAgentState:

	log.flow(f"Entered call_writer_agent")

	# FIXME: Original user query might be confusing
	state["messages"] = [msg for msg in state["messages"] if "tool_calls" not in msg.additional_kwargs]

	remaining_tasks = f"Remaining tasks:\n{AgentTaskList.from_list(state['unsolvedTasks']).for_agent()}"
	completed_tasks = f"Completed tasks:\n{AgentTaskList.from_list(state['completedTasks']).for_agent()}"
	
	tree_str = ""

	# TODO: Refactor duplicated code?
	if not state["blockTree"].is_empty():
		tree_mapping = client.index.to_int(state["blockTree"].get_all_nodes())

		#log.debug(f"Tree ids:", tree_mapping.values())
		tree_names = client.index.get_names(list(tree_mapping.values()))

		log.debug(f"Tree names:", {uuid: name for uuid, name in tree_names.items() if name != ""})

		for uuid, index in tree_mapping.items():
			if index in tree_names and tree_names[index] != "":
				tree_mapping[uuid] = f"{index}:{tree_names[index]}"
			else:
				tree_mapping[uuid] = f"{index}"

		tree_str = state['blockTree'].get_tree_str(tree_mapping)

		log.knowledge("\n\nVisited blocks for writer:\n", tree_str)

		tree_str = f"Tree of blocks visited:" + '\n' + tree_str
	else:
		log.error("Block tree is empty")
	
	visitedBlocks = f"All visited blocks (id : content):\n" + '\n'.join([f"{key} : {value}" for key, value in state["visitedBlocks"].items()])

	# TODO: Possibly reorder  visitedBlocks according to the block tree

	if state["actions"]:
		actions_str = "Actions taken:\n" + AgentActionListUtils.actions_to_string(state["actions"])

	messages_with_context = get_message_timeline_from_state(state)

	if state["unsolvedTasks"]:
		messages_with_context.append(AIMessage(content=remaining_tasks))
	if state["completedTasks"]:
		messages_with_context.append(AIMessage(content=completed_tasks))
	# TODO: Implement bool method that checks if visitedBlocks is empty
	if len(state["visitedBlocks"]) > 0:
		messages_with_context.append(AIMessage(content=visitedBlocks))
	else:
		raise ValueError("No block info in context")
	if not state["blockTree"].is_empty():
		messages_with_context.append(AIMessage(content=tree_str))
	if state["actions"]:
		messages_with_context.append(AIMessage(content=actions_str))
	# Add current time information to context
	messages_with_context.append(create_current_time_message())

	response = writer_agent_runnable.invoke({"messages": messages_with_context})

	state["messages"].append(response)

	return {
		"messages": state["messages"],
		"functionCalls": [],
		"recentResults": []
	}


def check_and_call_tools_wrapper(state: WriterAgentState) -> WriterAgentState:
	return check_and_call_tools(state, writer_tool_executor)


def response_check(state: WriterAgentState) -> str:

	log.knowledge(f"Unsolved tasks:", "\n".join([str(task) for task in state['unsolvedTasks']]))
	log.knowledge(f"Completed tasks:", "\n".join([str(task) for task in state['completedTasks']]))

	# FIXME: Task not found in unsolved tasks: 1

	if len(state["unsolvedTasks"]) == 0:
		for task in state["completedTasks"]:
			if task.status == "failed":
				log.error(f"Task failed: {task.name}")
				return "failed"

		log.flow(f"All writer tasks completed")
		return "completed"
	else:
		return "continue"


def clean_output(state: WriterAgentState):

	for msg in state["messages"]:
		msg.content = client.url_index.replace_placeholders(msg.content)

	return {"messages": state["messages"]}


graph = StateGraph(WriterAgentState)

graph.set_entry_point("writerStart")

graph.add_node("writerStart", writer_start)
graph.add_node("callWriterAgent", call_writer_agent)
graph.add_node("checkWriterTools", check_and_call_tools_wrapper)
graph.add_node("writerResponseCheck", clean_output)

graph.add_edge("writerStart", "callWriterAgent")
graph.add_edge("callWriterAgent", "checkWriterTools")
graph.add_edge("checkWriterTools", "writerResponseCheck")

graph.add_conditional_edges(
	"writerResponseCheck",
	response_check,
	{
		"completed": END,
		"failed": END,
		"continue": "callWriterAgent"
	}
)

writer_agent = graph.compile()