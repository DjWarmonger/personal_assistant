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
		task_id: str = Field(description="ID of the task to complete (eg. UUID or 01)")
		status: TaskStatus = Field(description="Status of the task after completion")
		answer: str = Field(description="If task is a question or query, provide detailed answer (ie. data, tables, etc). Otherwise briefly describe the result of the task.")

	args_schema: type[ArgsSchema] = ArgsSchema

	async def _arun(self, context: AgentState, task_id: str, status: TaskStatus, answer: str, **kwargs: Any) -> tuple[AgentState, str]:
		# Implement the async complete task logic with safe updates to context (state)
		async def modify_state(state: AgentState) -> AgentState:
			log.flow(f"Completing task: {task_id}")
			goal = ""
			for unsolved_task in state.unsolved_tasks:
				if str(unsolved_task.id) == str(task_id):
					goal = unsolved_task.goal
					break
			task = AgentTask(id=task_id, goal=goal)
			# Mark task as complete with the answer
			task.complete(answer)
			state.completed_tasks.add(task)
			if task in state.unsolved_tasks:
				state.unsolved_tasks.remove(task)
			else:
				log.error(f"Task not found in unsolved tasks: {task_id}")
			return state

		new_state = await context.async_update_state(modify_state)
		return new_state, f"Completed task {task_id} with answer: {answer}"


class AddTaskTool(ContextAwareTool):
	name: str = "add_task" 
	description: str = "Add a task to the agent's task list"

	class ArgsSchema(ContextAwareTool.ArgsSchema):
		task: AgentTask = Field(description="The task to add to the agent's task list")

	args_schema: type[ArgsSchema] = ArgsSchema

	async def _arun(self, context: AgentState, task: AgentTask, **kwargs: Any) -> tuple[AgentState, str]:
		# Implement async add task logic with safe state updates
		async def modify_state(state: AgentState) -> AgentState:
			log.flow(f"Adding task: {task.id}")
			state.unsolved_tasks.add(task)
			return state

		new_state = await context.async_update_state(modify_state)
		return new_state, f"Added task {task.id} to the agent's task list"

