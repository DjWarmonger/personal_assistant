from typing import Any, List
import json
import asyncio

from langchain_core.messages import BaseMessage, AIMessage
from langgraph.prebuilt import ToolExecutor

from tz_common import log
from .message import add_timestamp
from .agentState import AgentState
from tz_common.actions import AgentAction, AgentActionListUtils, ActionStatus


async def get_tool_result(tool, action: AgentAction, state: AgentState, input_args: dict) -> tuple[str, tuple[AgentState, str]]:
	try:
		# Workaround for args handling in langchain
		input_args["context"] = state
		context, result = await tool.arun(tool_input=input_args)
		return (action, (context, result))
	except Exception as e:
		# Attach the action to the exception context
		e.args = (action,) + e.args
		raise


def process_tool_calls(last_message, tool_executor : ToolExecutor, state: AgentState):

	tasks = []

	# Define all tasks to be executed asynchronously
	for tool_call in last_message.additional_kwargs["tool_calls"]:
		name = tool_call["function"]["name"]
		input_args = json.loads(tool_call["function"]["arguments"])
		for tool in tool_executor.tools:
			if tool.name == name:

				action = AgentAction.from_tool_call(name, tool_call["id"].rsplit('_', 1)[1], input_args)
				action.set_in_progress()
				state["actions"].append(action)

				tool_name = action.to_tool_call_string()
				log.flow(f"Calling tool: {tool_name}")

				#log.debug(f"Tool signature:", tool.args)
				log.debug(f"input_args:", input_args)

				# TODO: Set agent_id to calling agent
				# TODO: Store agent name in State?

				#log.debug(f"state:", state)
				tasks.append(get_tool_result(tool, action, state, input_args))


	async def call_tools():
		# Dispatch tool calls asynchronously
		try:
			results = await asyncio.gather(*tasks, return_exceptions=True)
			processed_results = {}
			for result in results:
				if isinstance(result, Exception):
					# Get the action from the exception context
					failed_action = result.args[0] if result.args else None
					# Get the actual error message (skip the action part)
					actual_error = result.args[1] if len(result.args) > 1 else str(result)
					
					if failed_action:
						error_message = f"Tool '{failed_action.to_tool_call_string()}' failed: {actual_error}"
						log.error(f"Call tool failed: {error_message}")
						failed_action.fail(actual_error)
						processed_results[failed_action.to_tool_call_string()] = (failed_action, actual_error)
					else:
						error_message = str(result)
						log.error(f"Call tool failed: {error_message}")
				else:
					action, (_, message) = result
					action.complete("Tool call succeeded")
					processed_results[action.to_tool_call_string()] = (action, message)
					# TODO: Add "related message" with tool output to action

			return processed_results

		except Exception as e:
			return {}

	try:
		loop = asyncio.new_event_loop()
		asyncio.set_event_loop(loop)
		processed_results = loop.run_until_complete(call_tools())
	finally:
		loop.close()

	for key, (action, message) in processed_results.items():
		tool_status = "SUCCESS" if action.status == ActionStatus.COMPLETED else "failed"
		tool_result_message = f"Result of tool {key}: {tool_status}, {message}"
		log.knowledge(f"Result of tool {key}: {tool_status}", message)

		# Show AI tool call -> result
		ai_message = AIMessage(content=tool_result_message)
		add_timestamp(ai_message)
		state["recentResults"].append(ai_message)
		state["toolResults"].append(ai_message)

		if action.status == ActionStatus.COMPLETED:
			log.debug(f"Tool call succeeded: {action.id}")
			#AgentActionListUtils.complete_action(state["actions"], action.id, "Tool call succeeded")
		elif action.status == ActionStatus.FAILED:
			log.debug(f"Tool call failed: {action.id}")
			#AgentActionListUtils.complete_action(state["actions"], action.id, "Tool call failed")

		# TODO: Handle IN_PROGRESS actions

	log.flow(f"Actions after tool calls: {len(state['actions'])}")

	return state


def check_and_call_tools(state: AgentState, tool_executor: ToolExecutor) -> AgentState:
	
	log.flow(f"Entered check_tools")

	if "recentResults" not in state:
		state["recentResults"] = []

	if "toolResults" not in state:
		state["toolResults"] = []

	if "actions" not in state:
		state["actions"] = []

	last_message = state["messages"][-1]
 
	if not last_message.additional_kwargs.get("tool_calls", []):
		log.flow(f"No tool calls")
		return {"messages": state["messages"], "functionCalls": []}

	processed_results = process_tool_calls(last_message, tool_executor, state)
	return processed_results