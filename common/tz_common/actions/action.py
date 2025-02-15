from enum import Enum
import uuid
from typing import List, Optional, Any, Iterator
from pydantic.v1 import BaseModel, Field
from collections.abc import Sequence


class ActionStatus(Enum):
	NOT_STARTED = 0
	IN_PROGRESS = 1
	COMPLETED = 2
	# Action cannot be blocked, it is either completed immediately or failed
	FAILED = 4


class AgentAction(BaseModel):
	"""Represents a single attempt to handle a task, like calling a tool or answering the question directly. If action fails, it is gone forever. Further attempts will need to spawn new action."""

	id: str = Field(default_factory=lambda: str(uuid.uuid4()))

	# TODO: Think about how to automagically set task_id and agent_id
	task_id: str = Field(description="Task that this action is trying to solve")
	agent_id: str = Field(default="", description="Agent that is performing this action. Can be empty if we assume there's only one agent")
	description: str = Field(description="What needs to be done in this action")
	
	related_messages: List[str] = Field(default_factory=list)
	related_documents: List[str] = Field(default_factory=list, description="Document may be related to URL, access it indirectly")
	status: ActionStatus = Field(default=ActionStatus.NOT_STARTED)
	resolution: Optional[str] = Field(default=None, description="What happened with this task - it was completed in a specific way, or expired, or nothing had to be done")


	@classmethod
	def from_tool_call(cls, tool_name: str, tool_call_id: str, args: dict) -> "AgentAction":
		return cls(
			id=tool_call_id,
			description=f"{tool_name} ({tool_call_id}) with args: {args}",
			# These fields are required by the model but not provided in tool calls
			task_id="default_task",  # TODO: Get from state/context
			agent_id=""  # Using default empty string
		)


	def to_tool_call_string(self):
		if not self.description:
			raise ValueError("Description is not set")

		return self.description.split(" with args")[0]


	def add_tool_result(self, uuid: str):
		# TODO: Actually recognize messages by uuid
		self.related_messages.append(uuid)

	
	def set_in_progress(self):
		self.status = ActionStatus.IN_PROGRESS


	def complete(self, resolution: str):
		self.status = ActionStatus.COMPLETED
		self.resolution = resolution


	def fail(self, resolution: str):
		self.status = ActionStatus.FAILED
		self.resolution = resolution


	def __str__(self) -> str:
		return f"{self.id} - {self.description} - {self.status.name}"

# TODO: Kolejny indeks akcji, który mapuje uuid na integer?


class AgentActionListUtils:

	def get_action_by_id(actions: List[AgentAction], id: str) -> AgentAction:
		for action in actions:
			if action.id == id:
				return action
		raise ValueError(f"Action with id {id} not found")
	

	def complete_action(actions: List[AgentAction], id: str, resolution: str):

		action = None
		for a in actions:
			if a.id == id:
				action = a
				break
		if action is None:
			return

		action.complete(resolution)


	def actions_to_string(actions: List[AgentAction]) -> str:
		return "\n".join([str(action) for action in actions])

