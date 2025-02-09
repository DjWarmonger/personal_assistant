from langchain_core.messages import AIMessage
from langgraph.graph import StateGraph, END


from tz_common.logs import log
from tz_common.tasks import TaskStatus
from tz_common.langchain_wrappers import check_and_call_tools

from agents import planner_agent_runnable, notion_agent_runnable, writer_agent_runnable
from agentTools import planner_tool_executor, client
from agentState import PlannerAgentState, NotionAgentState, WriterAgentState


def start(state: PlannerAgentState) -> PlannerAgentState:

	log.flow(f"Entered start")

	favourites = client.index.get_favourites_with_names(10)

	if favourites:
		message = f"Here are user's favourite pages. Prefer them if they are relevant to the task:\n"
		for favourite in favourites:
			message += f"{favourite[1]:<2} ({favourite[0]})\n"

		state["messages"].append(AIMessage(content=message))
	else:
		log.error(f"No favourites found")

	return {
		"messages": state["messages"],
		"functionCalls": [],
		"recentResults": [], # Probably not needed, since taks list is generated in one go
		"unsolvedTasks": set(),
		"completedTasks": set()
		}


def planning(state: PlannerAgentState) -> PlannerAgentState:

	log.flow(f"Entered planning")

	# FIXME: openai.BadRequestError: Error code: 400 - {'error': {'message': "An assistant message with 'tool_calls' must be followed by tool messages responding to each 'tool_call_id'. The following tool_call_ids did not have response messages: call_ZSna20F4g7BWjq75ieOj3rM5", 'type': 'invalid_request_error', 'param': 'messages', 'code': None}}

	state["messages"] = [msg for msg in state["messages"] if "tool_calls" not in msg.additional_kwargs]
	
	"""
	recent_calls = "Recent results of tool calls:\n"
	recent_calls += "\n\n".join([str(result.content) for result in state["recentResults"]])
	messages_with_context = state["messages"] + [AIMessage(content=recent_calls)]
	"""

	response = planner_agent_runnable.invoke({"messages": state["messages"]})

	state["messages"].append(response)

	return {"messages": state["messages"], "functionCalls": []}

	# TODO: Add favourites to prompt


	# TODO: Modify prompt so it can handle unsolved tasks from other agents

	# TODO: Add more context?
	"""
	task_list = planner_agent_runnable.invoke({"messages": state["messages"]})

	log.common("Task list:", task_list)
	log.knowledge(f"Task list:\n" + "\n".join(str(task) for task in task_list))


	for task in task_list:
		if task.status in [TaskStatus.NOT_STARTED, TaskStatus.IN_PROGRESS]:
			state["unsolved_tasks"].add(task)
		elif task.status == TaskStatus.COMPLETED:
			state["solved_tasks"].add(task)
		else:

			log.debug(f"Task status is {task.status}: {task.name}, skipping")
	"""

	return {
			"messages": state["messages"],
			#"unsolved_tasks": state["unsolved_tasks"],
			#"solved_tasks": state["solved_tasks"]
		}


def check_and_call_tools_wrapper(state: PlannerAgentState) -> PlannerAgentState:
	return check_and_call_tools(state, planner_tool_executor)


def call_agents(state: PlannerAgentState) -> PlannerAgentState:

	log.flow(f"Entered call_agents")

	if "unsolvedTasks" not in state:
		log.flow(f"No unsolved tasks found")
		return state


	for task in state["unsolvedTasks"].union(state["completedTasks"]):
		if task.status in [TaskStatus.NOT_STARTED, TaskStatus.IN_PROGRESS]:
			state["unsolvedTasks"].add(task)

		elif task.status == TaskStatus.COMPLETED:
			state["completedTasks"].add(task)
		else:
			log.debug(f"Task status is {task.status}: {task.name}, skipping")

	"""
	# TODO: Assign tasks to specific agents

	# TODO: Call notion agent and writer agent

	# TODO: Pass main requets to notion agent?

	notion_agent_state = NotionAgentState(
		unsolvedTasks=state["unsolvedTasks"],
		completedTasks=state["completedTasks"]
	)


	notion_agent_state = notion_agent_runnable.invoke(notion_agent_state)

	# TODO: pass main requets to writer agent?

	# TODO: Pass all retrieved pages to writer agent

	writer_agent_state = WriterAgentState(
		unsolvedTasks=state["unsolvedTasks"],
		completedTasks=state["completedTasks"]
	)


	writer_agent_state = writer_agent_runnable.invoke(writer_agent_state)

	# TODO: Actually return final response
	"""

	return {"messages": state["messages"], "functionCalls": []}


def check_tasks(state: PlannerAgentState) -> str:

	log.flow(f"Entered check_tasks")
	return "completed"

	# TODO: Define it as an enum somehwere

	# FIXME: This was called, so task list should be present:
	#$ Result of tool Xi4SkabF5gU20V2mqRaTqCic(SetTaskList):Task list set

	# TODO: Only check status of user task
	if "unsolvedTasks" not in state:
		log.flow(f"No unsolved tasks found")
		return "completed"

	if len(state["unsolvedTasks"]) == 0:
		for task in state["completedTasks"]:
			if task.status == "failed":

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



