import asyncio
from typing import Type, Any
from pydantic.v1 import BaseModel, Field

from tz_common.tasks import AgentTask, TaskRole, TaskStatus
from tz_common import log
from .tool import ContextAwareTool
from .agentState import AgentState

class CompleteTaskTool(ContextAwareTool):
	name: str = "complete_task"
	description: str = "Complete a task. Provide answer to the task question, if any."

	class ArgsSchema(ContextAwareTool.ArgsSchema):
		# TODO: Map UUID to integer
		task_id: str = Field(description="UUID of the task to complete")
		status: TaskStatus = Field(description="Status of the task after completion")
		resolution: str = Field(description="Brief resolution of the task, ie. achieved result or reason of failure.")
		data_output: str = Field(default="", description="Detailed output of the task, if any. If task is a question, request for information or query, provide detailed answer, including data, tables, etc in this field. Only leave this empty if it's actionable task and 'resolution' description is sufficient.")

	async def _run(self,
				context: AgentState,
				task_id: str,
				status: TaskStatus,
				resolution: str,
				data_output: str = "",
				**kwargs: Any) -> tuple[AgentState, str]:

		if not task_id:
			# TODO: Validate uuid in uuid class
			raise ValueError("Cannot complete task with empty ID")

		log.flow(f"Completing task: {task_id}")
		
		goal = None
		for unsolved_task in context["unsolvedTasks"]:
			if str(unsolved_task.id) == str(task_id):
				goal = unsolved_task.goal
				break

		if goal is None:
			# FIXME: If task id is wrong, then it won't be marked as failed
			for completed_task in context["completedTasks"]:
				if str(completed_task.id) == str(task_id):
					raise ValueError(f"Task is already completed: {task_id}")

			raise ValueError(f"Task not found in unsolved tasks: {task_id}")
		
		task = AgentTask(id=task_id, goal=goal)

		# TODO: Use status field
		task.complete(resolution, data_output)

		if task in context["unsolvedTasks"]:
			for i, unsolved_task in enumerate(context["unsolvedTasks"]):
				if str(unsolved_task.id) == str(task_id):
					del context["unsolvedTasks"][i]
					break
		else:
			for solved_task in context["completedTasks"]:
				if str(solved_task.id) == str(task_id):
					raise ValueError(f"Task already completed: {task_id}")

		context["completedTasks"].append(task)

		return context, f"Completed task {task_id} with resolution: {resolution}, output: {data_output}"


class AddTaskTool(ContextAwareTool):
	name: str = "add_task" 
	description: str = "Add a task to the agent's task list"

	class ArgsSchema(ContextAwareTool.ArgsSchema):
		#TODO: Use AgentTasl without boilerplate redefinition
		#task: AgentTask = Field(description="The task object to add to the agent's task list")

		role: TaskRole = Field(description=f"Who requested this task: {', '.join([role.name for role in TaskRole])}")
		role_id: str = Field(description="eg. user id, agent id")
		goal: str = Field(description="What needs to be done: Requirements and expected results, including format of the output")


	async def _run(self, context: AgentState, role: TaskRole, role_id: str, goal: str, **kwargs: Any) -> tuple[AgentState, str]:

		if type(role) == str:
			role = TaskRole[role.upper()]

		task = AgentTask(role=role, role_id=role_id, goal=goal)

		log.flow(f"Adding task: {task.id}: {task.goal}")
		context["unsolvedTasks"].append(task)
		return context, f"Added task {task.id} to the agent's task list"



