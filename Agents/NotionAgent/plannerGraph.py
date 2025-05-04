from langchain_core.messages import AIMessage
from langgraph.graph import StateGraph, END


from tz_common.logs import log
from tz_common.tasks import TaskStatus, TaskRole
from tz_common.langchain_wrappers import check_and_call_tools

from agents import planner_agent_runnable
from agentTools import planner_tool_executor, client
from agentState import PlannerAgentState, NotionAgentState, WriterAgentState
from graph import notion_agent
from writerGraph import writer_agent


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
	else:
		log.error(f"No favourites found")

	return {
		"initialPrompt": initial_prompt,
		"messages": state["messages"],
		"unsolvedTasks": set(),
		"completedTasks": set(),
		"actions": [],
		"toolResults": [],
		"recentResults": [],
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

	if "unsolvedTasks" not in state:
		log.error(f"No unsolved tasks found")
		return state
	
	# TODO: Update user query after chat reply

	unsolvedTasksNotion = set([task for task in state["unsolvedTasks"] if task.role_id.upper() == "NOTION" and task.is_todo()])

	for task in unsolvedTasksNotion:
		task.start()

	notion_agent_state = {
		"messages": state["messages"],
		"unsolvedTasks": list(unsolvedTasksNotion),
		#"unsolvedTasks": list(task for task in unsolvedTasksNotion),  # Convert set to list
		#"completedTasks": list(state["completedTasks"]), # Convert set to list
		"completedTasks": state["completedTasks"],
		"actions": [],
		"toolResults": [],
		"recentResults": [],
		"visitedBlocks": []
	}

	notion_agent_response = notion_agent.invoke(notion_agent_state)
	log.debug(f"Notion agent response:", notion_agent_response)

	# TODO: Read remaining tasks back from notion agent

	unsolvedTasksWriter = set([task for task in state["unsolvedTasks"] if task.role_id.upper() == "WRITER" and task.is_todo()])

	"""
	# FIXME: Automagically convert to dict
	writer_agent_state = WriterAgentState(
		messages=state["initialPrompt"],
		unsolvedTasks=list(unsolvedTasksWriter),
		completedTasks=notion_agent_response["completedTasks"],
		visitedBlocks=notion_agent_response["visitedBlocks"],
		blockTree=notion_agent_response["blockTree"],
		toolResults=[],
		recentResults=[]
	)
	"""

	writer_agent_state = {
		"messages": state["initialPrompt"],
		"unsolvedTasks": list(unsolvedTasksWriter),
		"completedTasks": notion_agent_response["completedTasks"],
		"visitedBlocks": notion_agent_response["visitedBlocks"],
		"blockTree": notion_agent_response["blockTree"],
		"toolResults": [],
		"recentResults": []
	}

	writer_agent_response = writer_agent.invoke(writer_agent_state)

	# TODO: Remember visited blocks for subsequent calls?

	return {"messages": state["messages"],
			"solvedTasks": list(set(writer_agent_state["completedTasks"])),
			"unsolvedTasks": list(set(writer_agent_state["unsolvedTasks"]))}


def check_tasks(state: PlannerAgentState) -> str:

	log.flow(f"Entered check_tasks")
	# TODO: Define it as an enum somehwere

	if "unsolvedTasks" not in state:
		log.error(f"No unsolved tasks found")
		return "failed"
	
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



