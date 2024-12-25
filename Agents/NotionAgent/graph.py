import json
from typing import TypedDict, Sequence, Optional
import asyncio

from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage, AIMessage, ToolMessage
from langgraph.prebuilt import ToolInvocation

from tz_common.logs import log
from tz_common import create_langfuse_handler
from agents import notion_agent_runnable
from langfuse.decorators import observe
from agentTools import tool_executor, client

import os
import time

langfuse_handler = create_langfuse_handler(user_id="Notion Agent")

class AgentState(TypedDict):

	messages: Sequence[BaseMessage]
	functionCalls: Sequence[BaseMessage] #One message can contain multiple tool calls
	#TODO: Limit number of actions agent can take
	#TODO: Remind agent about the limit


def call_tool(state) -> None:

	# TODO: More streamlined, common wrapper to call tools for every agent

	# We know the last message involves at least one tool call
	last_message = state["functionCalls"]

	tasks = []

	async def get_tool_result(tool, name: str, input_args: dict) -> tuple[str, str]:
		result = await tool.arun(tool_input=input_args)#, **input_args)
		return (name, result)
	
	for tool_call in last_message.additional_kwargs["tool_calls"]:
		
		name = tool_call["function"]["name"]
		input_args = json.loads(tool_call["function"]["arguments"])

		for tool in tool_executor.tools:
			if tool.name == name:
				tool_name = f"{tool_call['id'].rsplit('_', 1)[1]}({tool.name})"
				log.flow(f"Calling tool: {tool_name}")

				tasks.append(get_tool_result(tool, tool_name, input_args))

	async def call_tools():
		results = await asyncio.gather(*tasks)
		return dict(results)

	#start_time = time.time()
	results = asyncio.run(call_tools())
	#end_time = time.time()
	#log.debug(f"Tool calls took {end_time - start_time} seconds")

	for key, result in results.items():
		log.debug(f"Result:", result)
		# FIXME: Quote markk at the beginning: "jieUsS3NXOAlfqzN2axiFYd4(NotionGetChildren) returned:
		message = f"{key} returned:\n{result}"
		state["messages"].append(AIMessage(content=message))

	log.flow(f"Size of messages: {len(state['messages'])}")

	return {"messages": state["messages"], "functionCalls": []}


def start(state: AgentState) -> AgentState:

	#log.flow(f"Entered start")

	return {"messages": state["messages"], "functionCalls": []}

#@observe()
def call_notion_agent(state: AgentState) -> AgentState:

	#log.flow(f"Entered call_notion_agent")

	state["messages"] = [msg for msg in state["messages"] if "tool_calls" not in msg.additional_kwargs]

	response = notion_agent_runnable.invoke({"messages": state["messages"]})

	state["messages"].append(response)

	return {"messages": state["messages"], "functionCalls": []}


def check_tools(state: AgentState) -> AgentState:

	log.flow(f"Entered check_tools")

	last_message = state["messages"][-1]

	if last_message:

		log.debug(f"Last message:\n", str(last_message))

		# If there are no tool calls, then we finish
		if "tool_calls" in last_message.additional_kwargs:
			state["functionCalls"] = last_message
			log.flow(f"Calling tools")

			ret =  call_tool(state)

			log.debug(f"Returned from tool calls:\n", ret)

			return ret

	# Otherwise, we continue
	log.flow(f"No tool calls")
	return {"messages": state["messages"]}


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
	
	# TODO: Save index when response is returned?

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
graph.add_node("checkTools", check_tools)
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