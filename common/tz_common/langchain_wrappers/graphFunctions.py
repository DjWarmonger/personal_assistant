from typing import Any
import json
import asyncio

from langchain_core.messages import BaseMessage, AIMessage
from langgraph.prebuilt import ToolExecutor

from tz_common import log
from .agentState import AgentState


async def get_tool_result(tool, tool_name: str, state: AgentState, input_args: dict, ) -> tuple[str, str]:

	#log.debug(f"arun input_args:", input_args)
	#log.debug(f"arun state:", state)

	# Workaround for args handling in langchain
	input_args["context"] = state

	result = await tool.arun(tool_input=input_args)
	return (tool_name, result)


def process_tool_calls(last_message, tool_executor : ToolExecutor, state: AgentState):

	tasks = []

	# Define all tasks to be executed asynchronously
	for tool_call in last_message.additional_kwargs["tool_calls"]:
		name = tool_call["function"]["name"]
		input_args = json.loads(tool_call["function"]["arguments"])
		for tool in tool_executor.tools:
			if tool.name == name:

				# TODO: log actual inpup parameters signature
				tool_name = f"{tool_call['id'].rsplit('_', 1)[1]}({tool.name})"
				log.flow(f"Calling tool: {tool_name}")

				#log.debug(f"Tool signature:", tool.args)
				log.debug(f"input_args:", input_args)

				# FIXME: Incorrect input_args
				# input_args:{'__arg1': '1'}

				#log.debug(f"state:", state)
				tasks.append(get_tool_result(tool, tool_name, state, input_args))

	async def call_tools():
		# Dispatch tool calls asynchronously
		try:
			results = await asyncio.gather(*tasks, return_exceptions=True)
			processed_results = {}
			for result in results:
				if isinstance(result, Exception):
					error_message = str(result)

					log.error(f"Error: {error_message}")
					processed_results[result.__class__.__name__] = error_message
				else:
					# Append results - Only message
					key, value = result
					processed_results[key] = value[-1]

			return processed_results

		except Exception as e:
			return {"error": str(e)}

	try:
		loop = asyncio.new_event_loop()
		asyncio.set_event_loop(loop)
		processed_results = loop.run_until_complete(call_tools())
	finally:
		loop.close()

	for key, result in processed_results.items():
		log.debug("Result:", result)
		message = f"{key} returned:\n{result}"
		ai_message = AIMessage(content=message)
		state["recentResults"].append(ai_message)
		state["toolResults"].append(ai_message)
		#state = trim_recent_results(state)

	return state


def check_and_call_tools(state: AgentState, tool_executor: ToolExecutor) -> AgentState:
	
	log.flow(f"Entered check_tools")

	if "recentResults" not in state:
		state["recentResults"] = []

	if "toolResults" not in state:
		state["toolResults"] = []

	last_message = state["messages"][-1]
 
	if not last_message.additional_kwargs.get("tool_calls", []):
		log.flow(f"No tool calls")
		return {"messages": state["messages"], "functionCalls": []}

	processed_results = process_tool_calls(last_message, tool_executor, state)
	return processed_results