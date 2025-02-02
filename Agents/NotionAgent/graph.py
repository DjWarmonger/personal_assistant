import json
from typing import TypedDict, Sequence, Optional
import asyncio

from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage, AIMessage, ToolMessage

from tz_common.logs import log
from tz_common import create_langfuse_handler
from tz_common.langchain_wrappers import AgentState, check_and_call_tools
from agents import notion_agent_runnable
from langfuse.decorators import observe
from agentTools import tool_executor, client

import os
import time

langfuse_handler = create_langfuse_handler(user_id="Notion Agent")

class NotionAgentState(AgentState):
	pass


def start(state: NotionAgentState) -> NotionAgentState:

	# TODO: Consider  exporting to library?

	log.flow(f"Entered start")

	favourites = client.index.get_favourites_with_names(10)

	# TODO: Add visit count?

	if favourites:
		message = f"Here are user's favourite pages. Start with them if they are relevant to the task:\n"
		for favourite in favourites:
			message += f"{favourite[1]:<2} ({favourite[0]})\n"

		state["messages"].append(AIMessage(content=message))
	else:
		log.error(f"No favourites found")

	return {"messages": state["messages"], "functionCalls": []}


def call_notion_agent(state: AgentState) -> AgentState:

	#log.flow(f"Entered call_notion_agent")

	state["messages"] = [msg for msg in state["messages"] if "tool_calls" not in msg.additional_kwargs]

	response = notion_agent_runnable.invoke({"messages": state["messages"]})

	state["messages"].append(response)

	return {"messages": state["messages"], "functionCalls": []}


def check_and_call_tools_wrapper(state: AgentState) -> AgentState:
	return check_and_call_tools(state, tool_executor)


def response_check(state: AgentState) -> str:

	# TODO: Use AgentAction, ActionStatus
	#log.flow(f"Entered response_check")

	response = state["messages"][-1]

	if "TASK_COMPLETED" in response.content:
		log.flow(f"Task completed")
		# FIXME: TASK_COMPLETED should be removed from visible message
		state["messages"][-1].content.replace("TASK_COMPLETED", "")
		return "completed"
	
	elif "TASK_FAILED" in response.content:
		log.error(f"Task failed")
		state["messages"][-1].content.replace("TASK_FAILED", "")
		return "failed"
	
	elif "HUMAN_FEEDBACK_NEEDED" in response.content:
		log.flow(f"Human feedback needed")
		state["messages"][-1].content.replace("HUMAN_FEEDBACK_NEEDED", "")
		return "human_feedback_needed"
	
	elif "AGENT_QUESTION" in response.content:
		log.flow(f"Agent question")
		state["messages"][-1].content.replace("AGENT_QUESTION", "")
		return "agent_question"

	else:
		return "continue"
	
# TODO: Rename if it works
def empty_action(state: AgentState):

	for msg in state["messages"]:
		msg.content = client.url_index.replace_placeholders(msg.content)

	#client.save_now()

	return {"messages": state["messages"]}


graph = StateGraph(AgentState)

graph.set_entry_point("start")

graph.add_node("start", start)
graph.add_node("callNotionAgent", call_notion_agent)
# FIXME: TypeError: check_and_call_tools() missing 1 required positional argument: 'tool_executor'
graph.add_node("checkTools", check_and_call_tools_wrapper)
graph.add_node("responseCheck", empty_action)

graph.add_edge("start", "callNotionAgent")
graph.add_edge("callNotionAgent", "checkTools")
graph.add_edge("checkTools", "responseCheck")

graph.add_conditional_edges(
	"responseCheck",
	response_check,
	{
		"completed": END,
		"failed": END,
		"human_feedback_needed": END,
		"agent_question": END,
		"continue": "callNotionAgent"
	}
)

app = graph.compile()