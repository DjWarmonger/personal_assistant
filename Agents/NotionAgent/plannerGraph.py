from langchain_core.messages import AIMessage
from langgraph.graph import StateGraph, END


from tz_common.logs import log
from tz_common.tasks import TaskStatus, TaskRole
from tz_common.langchain_wrappers import check_and_call_tools

from agents import planner_agent_runnable, notion_agent_runnable, writer_agent_runnable
from agentTools import planner_tool_executor, client
from agentState import PlannerAgentState, NotionAgentState, WriterAgentState
from graph import notion_agent, langfuse_handler


def start(state: PlannerAgentState) -> PlannerAgentState:

	log.flow(f"Entered start")

	# TODO: Analyze situations when there's more than one initial message
	state["initialPrompt"] = [state["messages"]]

	favourites = client.index.get_favourites_with_names(10)

	if favourites:
		message = f"Here are user's favourite pages (page title, index id). Provide their index if they are relevant to the task:\n"
		for favourite in favourites:
			message += f"{favourite[1]:<2} ({favourite[0]})\n"


		state["messages"].append(AIMessage(content=message))
	else:
		log.error(f"No favourites found")

	return {
		"messages": state["messages"],
		"unsolvedTasks": set(),
		"completedTasks": set(),
		"actions": [],
		"toolResults": [],
		"recentResults": []
		}


def planning(state: PlannerAgentState) -> PlannerAgentState:

	log.flow(f"Entered planning")

	state["messages"] = [msg for msg in state["messages"] if "tool_calls" not in msg.additional_kwargs]

	response = planner_agent_runnable.invoke({"messages": state["messages"]})

	state["messages"].append(response)

	return {"messages": state["messages"]}

	# TODO: Modify prompt so it can handle unsolved tasks from other agents


def check_and_call_tools_wrapper(state: PlannerAgentState) -> PlannerAgentState:
	return check_and_call_tools(state, planner_tool_executor)


def call_agents(state: PlannerAgentState) -> PlannerAgentState:

	log.flow(f"Entered call_agents")

	log.debug(f"Planner agent state type:", type(state))
	log.debug(f"Planner agent state:", state)


	# TODO: Why it is not a dict?
	log.debug(f"State before call_agents:", "\n".join([f"{k}: {v}" for k, v in state.items()]))

	if "unsolvedTasks" not in state:
		log.error(f"No unsolved tasks found")
		return state
	
	# TODO: Update user query after chat reply

	# TODO: Pass main requets to notion agent?

	# TODO: Pass messages list (?) to notion agent

	# TODO: Convert each agent call to separate nodes

	unsolvedTasksNotion = set([task for task in state["unsolvedTasks"] if task.role_id.upper() == "NOTION" and task.is_todo()])


	"""
	notion_agent_state = NotionAgentState(
		messages=state["initialPrompt"],
		unsolvedTasks=unsolvedTasksNotion,
		completedTasks=state["completedTasks"]
	)
	"""
	notion_agent_state = {
		"messages": state["messages"],
		"unsolvedTasks": list(unsolvedTasksNotion),
		#"unsolvedTasks": list(task for task in unsolvedTasksNotion),  # Convert set to list
		#"completedTasks": list(state["completedTasks"]), # Convert set to list
		"completedTasks": state["completedTasks"],
		"actions": [],
		"toolResults": [],
		"recentResults": []
	}

	log.debug("State before notion agent:", {
		k: type(v) for k, v in notion_agent_state.items()
	})

	notion_agent_response = notion_agent.invoke(notion_agent_state)#, config={"callbacks": [langfuse_handler]})

	log.debug(f"Notion agent response:", notion_agent_response)


	# TODO: Read remaining tasks back from notion agent

	# TODO: pass messages list (?) to writer agent

	unsolvedTasksWriter = set([task for task in state["unsolvedTasks"] if task.role_id.upper() == "WRITER" and task.is_todo()])


	writer_agent_state = WriterAgentState(
		messages=state["initialPrompt"],
		unsolvedTasks=unsolvedTasksWriter,
		completedTasks=notion_agent_response["completedTasks"],
		visitedBlocks=notion_agent_response["visitedBlocks"],
		block_tree=notion_agent_response["blockTree"]
	)

	log.debug(f"Writer agent state:", writer_agent_state)

	return writer_agent_state

	writer_agent_response = writer_agent_runnable.invoke(writer_agent_state)

	log.debug(f"Writer agent response:", writer_agent_response)


	# TODO: Read final response from writer agent
	"""
	# TODO: pass main requets to writer agent?



	# TODO: Pass all retrieved pages to writer agent

	writer_agent_state = WriterAgentState(
		unsolvedTasks=state["unsolvedTasks"],
		completedTasks=state["completedTasks"]
	)


	# TODO: Actually return final response
	"""

	# TODO: Remember visited blocks for subsequent calls?

	return {"messages": state["messages"],
			"solvedTasks": writer_agent_state["completedTasks"],
			"unsolvedTasks": writer_agent_state["unsolvedTasks"]}



def check_tasks(state: PlannerAgentState) -> str:

	log.flow(f"Entered check_tasks")
	#return "completed"

	# TODO: Define it as an enum somehwere

	# FIXME: This was called, so task list should be present:
	#$ Result of tool Xi4SkabF5gU20V2mqRaTqCic(SetTaskList):Task list set

	# TODO: Only check status of user task
	if "unsolvedTasks" not in state:
		log.error(f"No unsolved tasks found")
		return "failed"
	
	final_answer = ""

	if len(state["unsolvedTasks"]) == 0:
		for task in state["completedTasks"]:

			if task.role == TaskRole.USER:
				
				state["messages"].append(AIMessage(content=task.data_output))

			if task.status == TaskStatus.FAILED:

				log.error(f"Task failed: {task.name}")

				return "failed"

		log.flow(f"All tasks completed")
		return "completed"

	# TODO: Handle human feedback tool
	return "continue"


def handle_output(state: PlannerAgentState):

	log.knowledge(f"Current task list:", sorted(state['unsolvedTasks'].union(state['completedTasks'])))

	return {"messages": state["messages"]}


planner_graph = StateGraph(PlannerAgentState)

planner_graph.set_entry_point("start")

planner_graph.add_node("start", start)
planner_graph.add_node("planning", planning)
planner_graph.add_node("checkTools", check_and_call_tools_wrapper)
planner_graph.add_node("callAgents", call_agents)
planner_graph.add_node("checkTasks", handle_output)

planner_graph.add_edge("start", "planning")
planner_graph.add_edge("planning", "checkTools")
planner_graph.add_edge("checkTools", "callAgents")
planner_graph.add_edge("callAgents", "checkTasks")

planner_graph.add_conditional_edges(
	"checkTasks",
	check_tasks,
	{
		"completed": END,
		"failed": END,
		"continue": "planning"
	}
)


planner_runnable = planner_graph.compile()



