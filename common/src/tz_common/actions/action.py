from enum import Enum
import uuid
from typing import List, Optional, Any, Iterator
from collections.abc import Sequence
from datetime import datetime, timezone

from pydantic.v1 import BaseModel, Field

class ActionStatus(Enum):
	NOT_STARTED = 0
	IN_PROGRESS = 1
	COMPLETED = 2
	# Action cannot be blocked, it is either completed immediately or failed
	FAILED = 4


class AgentAction(BaseModel):
	"""Represents a single attempt to handle a task, like calling a tool or answering the question directly. If action fails, it is gone forever. Further attempts will need to spawn new action."""

	id: str = Field(default_factory=lambda: str(uuid.uuid4()))
	created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Timestamp when this action was created")

	# TODO: Think about how to automagically set task_id and agent_id
	task_id: str = Field(description="Task that this action is trying to solve")
	agent_id: str = Field(default="", description="Agent that is performing this action. Can be empty if we assume there's only one agent")
	description: str = Field(description="What needs to be done in this action")
	
	related_messages: List[str] = Field(default_factory=list)
	related_documents: List[str] = Field(default_factory=list, description="Document may be related to URL, access it indirectly")
	status: ActionStatus = Field(default=ActionStatus.NOT_STARTED)
	resolution: Optional[str] = Field(default=None, description="What happened with this task - it was completed in a specific way, or expired, or nothing had to be done")
	# TODO: Add timestamp


	@classmethod
	def from_tool_call(cls, tool_name: str, tool_call_id: str, args: dict) -> "AgentAction":
		# Clean up args description by removing "equals" from date filters
		args_str = str(args)
		# Remove "equals": from date filters to make them more readable
		args_str = args_str.replace('"equals":', '').replace("'equals':", '')
		
		return cls(
			id=tool_call_id,
			description=f"{tool_name} ({tool_call_id}) with args: {args_str}",
			# These fields are required by the model but not provided in tool calls
			# FIXME: Get from state/context
			task_id="",
			# TODO: Get from state/context
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


	# TODO: This is not used anywhere
	def complete(self, resolution: str):
		# TODO: Set separate timestamp for completion for statistics?
		self.status = ActionStatus.COMPLETED
		self.resolution = resolution


	def fail(self, resolution: str):
		self.status = ActionStatus.FAILED
		self.resolution = resolution


	def get_timestamp(self) -> datetime:
		return self.created_at


	def get_timestamp_str(self) -> str:
		return self.created_at.strftime("%Y-%m-%d %H:%M:%S")


	def __str__(self) -> str:
		return f"{self.status.name:10} {self.id} - {self.description[:200]}{'...' if len(self.description) > 200 else ''}"
	

	def __repr__(self) -> str:
		"""Provide a clean representation excluding empty fields for error messages."""
		fields = []
		
		# Always include id and status
		fields.append(f"id='{self.id}'")
		fields.append(f"status={self.status.name}")
		
		# Only include non-empty fields
		if self.task_id:
			fields.append(f"task_id='{self.task_id}'")
		if self.agent_id:
			fields.append(f"agent_id='{self.agent_id}'")
		if self.description:
			# Truncate long descriptions
			desc = self.description[:100] + '...' if len(self.description) > 100 else self.description
			fields.append(f"description='{desc}'")
		if self.related_messages:
			fields.append(f"related_messages={len(self.related_messages)} items")
		if self.related_documents:
			fields.append(f"related_documents={len(self.related_documents)} items")
		if self.resolution:
			fields.append(f"resolution='{self.resolution}'")
		
		return f"AgentAction({', '.join(fields)})"


	def __hash__(self):
		return hash(self.id)
	

	def __lt__(self, other) -> bool:
		"""
		Implement less than comparison for AgentAction objects.
		Compares based on action IDs to enable sorting.
		"""
		if not isinstance(other, AgentAction):
			return NotImplemented
		return str(self.id) < str(other.id)

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


	def create_failed_action(resolution: str, id: str = "") -> AgentAction:

		# TODO: Identify input action
		return AgentAction(
			id=id,
			description="",
			resolution=resolution,
			status=ActionStatus.FAILED,
		)
