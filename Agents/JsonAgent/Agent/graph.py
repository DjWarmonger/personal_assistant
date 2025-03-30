from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage, AIMessage, HumanMessage
from langfuse.decorators import observe

from tz_common.logs import log, LogLevel
from tz_common import create_langfuse_handler
from tz_common.langchain_wrappers import AgentState, trim_recent_results, check_and_call_tools, add_timestamp
from tz_common.tasks import AgentTaskList
from tz_common.actions import AgentActionListUtils, ActionStatus

from .prompt import json_agent_runnable
from .agentTools import tool_executor
from .agentState import JsonAgentState
from operations.summarize_json import truncated_json_format
# Create langfuse handler for logging
langfuse_handler = create_langfuse_handler(user_id="Json Agent")
log.set_log_level(LogLevel.FLOW)


def start(state: JsonAgentState) -> JsonAgentState:
	"""Initialize the JsonAgent state."""
	log.flow(f"Json Agent: Entered start")

	#log.debug(f"AgentState:", state)

	# TODO: json_doc and final_json_doc should be initialized from initial_json_doc
	if not state.get("json_doc"):
		state["json_doc"] = state["initial_json_doc"]

	return {
		"messages": state["messages"],
		"actions": [],
		"toolResults": [],
		"recentResults": [],
		"initial_json_doc": state.get("initial_json_doc", {}),
		"json_doc": state.get("json_doc", {}),
		"final_json_doc": state.get("final_json_doc", {}),
		"user_response": ""
	}


def call_json_agent(state: JsonAgentState) -> JsonAgentState:
	"""Call the JsonAgent with the current state."""
	log.flow(f"Entered call_json_agent")

	# Filter out messages with tool calls
	state["messages"] = [msg for msg in state["messages"] if "tool_calls" not in msg.additional_kwargs]

	# Create a list of tuples (timestamp, content, type) for both messages and actions
	timeline = []
	
	# Add messages to timeline
	for msg in state["messages"]:
		timestamp = msg.response_metadata.get("timestamp")
		timeline.append((timestamp, msg, "message"))
		log.debug(f"Message timestamp: {timestamp}")

	# Add actions to timeline
	if state["actions"]:
		for action in state["actions"]:
			timestamp = action.get_timestamp()
			timeline.append((timestamp, action, "action"))
			log.debug(f"Action timestamp: {action.get_timestamp_str()}")

	# Sort timeline by timestamp
	timeline.sort(key=lambda x: x[0])

	# Build context with temporary messages (not persisted to history)
	messages_with_context = []
	
	# Add messages and actions in chronological order
	for _, item, item_type in timeline:
		if item_type == "message":
			messages_with_context.append(item)
		elif item_type == "action":
			messages_with_context.append(AIMessage(content=f"Action taken: {str(item)}"))

	# Trim recent results to prevent context window overflow
	state = trim_recent_results(state, 2000)
	recent_calls = "Recent results of tool calls:\n"
	recent_calls += "\n\n".join([str(result.content) for result in state["recentResults"]])

	# Add document state
	document_state_str = f"""
Outline of loaded documents:
* Initial document:
{f"Loaded: {truncated_json_format(state['initial_json_doc'], max_depth=4, max_array_items=3, max_object_props=5, format_output=False)}" if state['initial_json_doc'] else "EMPTY"}
* Working document:
{f"Loaded: {truncated_json_format(state['json_doc'], max_depth=4, max_array_items=3, max_object_props=10, format_output=False)}" if state['json_doc'] else "EMPTY"}
* Final document:
{f"Loaded: {truncated_json_format(state['final_json_doc'], max_depth=4, max_array_items=3, max_object_props=5, format_output=False)}" if state['final_json_doc'] else "EMPTY"}
	"""

	messages_with_context.append(AIMessage(content=document_state_str))

	if state["recentResults"]:
		messages_with_context.append(AIMessage(content=recent_calls))

	# TODO: Tell agent names of documents loaded in a memory

	context = '\n'.join([f"{'user' if isinstance(message, HumanMessage) else 'assistant'}: {message.content}" for message in messages_with_context])
	log.knowledge("Messages with context:\n", context)

	# Invoke the agent with the context
	response = json_agent_runnable.invoke({"messages": messages_with_context})

	# Add response to messages
	add_timestamp(response)

	state["messages"].append(response)
	log.debug(f"Length of messages: {len(state['messages'])}")

	return {
		"messages": state["messages"],
		"functionCalls": [],
		"recentResults": []
	}


def check_and_call_tools_wrapper(state: AgentState) -> AgentState:
	"""Wrapper for checking and calling tools."""
	state = check_and_call_tools(state, tool_executor)

	if "actions" in state:
		for i, action in enumerate(state["actions"]):
			if action.status == ActionStatus.IN_PROGRESS:
				# FIXME: Should set message for this completion, which is tool result
			# TODO: Find message in recentResults by action id?
				action.complete("Finished")

	return state


def response_check(state: AgentState) -> str:

	# FIXME: No tool calls - but agent doesn't finish the loop

	# TODO: Allow agent just return response to user
	# TODO: Create single task? OR create single tool to return response to user?

	"""Check if all tasks are completed or if the agent should continue.
	log.knowledge(f"Unsolved tasks:", "\n".join([str(task) for task in state['unsolvedTasks']]))
	log.knowledge(f"Completed tasks:", "\n".join([str(task) for task in state['completedTasks']]))

	if len(state["unsolvedTasks"]) == 0:
		for task in state["completedTasks"]:
			if task.status == "failed":
				log.error(f"Task failed: {task.name}")
				return "failed"

		log.flow(f"All tasks completed")
		return "completed"
	else:
		return "continue"
	"""
	if state["user_response"]:
		log.flow(f"User response found: {state['user_response']}")
		return "completed"
	elif not state["recentResults"]:
		log.flow(f"No recent results of tool calls")
		# FIXME: We're here even though agent returned a response?
		# Maybe we do not need separate tool for response?
		return "completed"
	else:
		log.flow(f"No user response or recent results")
		return "continue"


def clean_output(state: AgentState):
	"""Clean up the state before returning to the user."""

	# TODO: Return all the context so it can be reused for next chat iteration
	return {"messages": state["messages"]}


# Create and configure the graph
graph = StateGraph(JsonAgentState)

graph.set_entry_point("jsonAgentStart")

graph.add_node("jsonAgentStart", start)
graph.add_node("callJsonAgent", call_json_agent)
graph.add_node("checkJsonTools", check_and_call_tools_wrapper)
graph.add_node("finalResponseCheck", clean_output)

graph.add_edge("jsonAgentStart", "callJsonAgent")
graph.add_edge("callJsonAgent", "checkJsonTools")
graph.add_edge("checkJsonTools", "finalResponseCheck")

graph.add_conditional_edges(
	"finalResponseCheck",
	response_check,
	{
		"completed": END,
		"failed": END,
		"human_feedback_needed": END,
		"agent_question": END,
		"continue": "callJsonAgent"
	}
)

json_agent = graph.compile()
