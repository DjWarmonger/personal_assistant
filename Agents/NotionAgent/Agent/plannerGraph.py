from langchain_core.messages import AIMessage
from langgraph.graph import StateGraph, END
from enum import Enum

from tz_common.logs import log
from tz_common.tasks import TaskStatus, TaskRole
from tz_common.langchain_wrappers import check_and_call_tools, get_message_timeline_from_state, add_timestamp
from tz_common.langchain_wrappers.message import create_current_time_message

from .agents import planner_agent_runnable
from .agentTools import planner_tool_executor, client
from .agentState import PlannerAgentState, NotionAgentState, WriterAgentState
from .graph import notion_agent
from .writerGraph import writer_agent
from operations.blocks.blockTree import BlockTree
from operations.blocks.blockDict import BlockDict


def planner_start(state: PlannerAgentState) -> PlannerAgentState:

	log.flow(f"Entered start")

	# TODO: Analyze situations when there's more than one initial message
	initial_prompt = state["messages"]

	favourites = client.index.get_favourites_with_names(10)

	if favourites:
		message = f"Here are user's favourite pages (page title, index id). Provide their index if they are relevant to the task:\n"
		for favourite in favourites:
			message += f"{favourite[1]:<2} ({favourite[0]})\n"


		state["messages"].append(AIMessage(content=message))
		add_timestamp(state["messages"][-1])
	else:
		log.error(f"No favourites found")

	return {
		"initialPrompt": initial_prompt,
		"messages": state["messages"],
		"unsolvedTasks": [],
		"completedTasks": [],
		"actions": [],
		"toolResults": [],
		"recentResults": [],
		}


def planning(state: PlannerAgentState) -> PlannerAgentState:

	log.flow(f"Entered planning")

	if "blockTree" not in state:
		raise KeyError("blockTree missing in planner state at planning")

	state["messages"] = [msg for msg in state["messages"] if "tool_calls" not in msg.additional_kwargs]
	messages_in_order = get_message_timeline_from_state(state)

	# Add current time information to context
	messages_in_order.append(create_current_time_message())

	response = planner_agent_runnable.invoke({"messages": messages_in_order})

	state["messages"].append(response)

	return {"messages": state["messages"]}

	# TODO: Modify prompt so it can handle unsolved tasks from other agents


def check_and_call_tools_wrapper(state: PlannerAgentState) -> PlannerAgentState:

	if "blockTree" not in state:
		raise KeyError("blockTree missing in planner state at call_and_check_tools")

	return check_and_call_tools(state, planner_tool_executor)


def call_agents(state: PlannerAgentState) -> PlannerAgentState:

	log.flow(f"Entered call_agents")

	if "blockTree" not in state:
		raise KeyError("blockTree missing in planner state at call_agents")

	if "unsolvedTasks" not in state:
		log.error(f"No unsolved tasks found")
		return state
	
	# TODO: Update user query after chat reply

	unsolvedTasksNotion = list(set([task for task in state["unsolvedTasks"] if task.role_id.upper() == "NOTION" and task.is_todo()]))

	for task in unsolvedTasksNotion:
		task.start()

	notion_agent_state = {
		"messages": state["messages"],
		"unsolvedTasks": unsolvedTasksNotion,
		"completedTasks": state["completedTasks"],
		"actions": [],
		"toolResults": [],
		"recentResults": [],
		"visitedBlocks": BlockDict()
	}

	notion_agent_response = notion_agent.invoke(notion_agent_state)

	if "blockTree" not in notion_agent_response:
		raise KeyError("blockTree missing in notion agent response at call_agents")
	if notion_agent_response["blockTree"].is_empty():
		log.error("blockTree is empty in notion agent response at call_agents")

	notion_agent_readable_response = notion_agent_response.copy()
	# Log blockTree as string representation
	notion_agent_readable_response["blockTree"] = str(notion_agent_response["blockTree"])
	log.debug(f"Notion agent response:", notion_agent_readable_response)

	# TODO: Read remaining tasks back from notion agent

	unsolvedTasksWriter = list(set([task for task in state["unsolvedTasks"] if task.role_id.upper() == "WRITER" and task.is_todo()]))

	if unsolvedTasksWriter:

		writer_agent_state = {
			"messages": state["initialPrompt"],
			"unsolvedTasks": list(unsolvedTasksWriter),
			"completedTasks": [],
			#"completedTasks": notion_agent_response["completedTasks"],
			"visitedBlocks": notion_agent_response["visitedBlocks"],
			"blockTree": notion_agent_response["blockTree"],
			"toolResults": [],
			"recentResults": []
		}

		writer_agent_response = writer_agent.invoke(writer_agent_state)
		log.debug(f"Writer agent response:", writer_agent_response)

		# FIXME: If writer is not called, then what is returned?

		return {"messages": state["messages"],
				"completedTasks": list(set(writer_agent_response["completedTasks"])),
				"unsolvedTasks": list(set(writer_agent_response["unsolvedTasks"]))}
	
	else:

		return {"messages": state["messages"],
				"completedTasks": list(set(notion_agent_response["completedTasks"])),
				"unsolvedTasks": list(set(notion_agent_response["unsolvedTasks"]))}
	
	# TODO: what if there were no tasks for notion agent either?

	# TODO: Remember visited blocks for subsequent calls?


def check_tasks(state: PlannerAgentState) -> str:

	log.flow(f"Entered check_tasks")
	# TODO: Define it as an enum somehwere

	if "unsolvedTasks" not in state:
		log.error(f"No unsolved tasks found")
		return "failed"
	
	if len(state["unsolvedTasks"]) == 0:
		for task in state["completedTasks"]:

			if task.role == TaskRole.USER:
				
				log.debug(f"User task completed: {task.goal}")
				state["messages"].append(AIMessage(content=task.data_output))

			if task.status == TaskStatus.FAILED:

				log.error(f"Task failed: {task.goal}")

				return "failed"

		log.flow(f"All tasks completed")
		return "completed"

	# TODO: Handle human feedback tool
	return "continue"


def handle_output(state: PlannerAgentState):

	log.knowledge(f"Current task list:", sorted(list(set(state['unsolvedTasks']) | set(state['completedTasks']))))

	return {"messages": state["messages"]}


planner_graph = StateGraph(PlannerAgentState)

planner_graph.set_entry_point("plannerStart")

planner_graph.add_node("plannerStart", planner_start)
planner_graph.add_node("planning", planning)
planner_graph.add_node("checkPlannerTools", check_and_call_tools_wrapper)
planner_graph.add_node("callAgents", call_agents)
planner_graph.add_node("checkPlannerTasks", handle_output)

planner_graph.add_edge("plannerStart", "planning")
planner_graph.add_edge("planning", "checkPlannerTools")
planner_graph.add_edge("checkPlannerTools", "callAgents")
planner_graph.add_edge("callAgents", "checkPlannerTasks")

planner_graph.add_conditional_edges(
	"checkPlannerTasks",
	check_tasks,
	{
		"completed": END,
		"failed": END,
		"continue": "planning"
	}
)


planner_runnable = planner_graph.compile()



