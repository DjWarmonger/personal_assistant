from enum import Enum
import uuid
from typing import Optional, List

from pydantic.v1 import BaseModel, Field

class TaskStatus(Enum):
	NOT_STARTED = 0
	IN_PROGRESS = 1
	COMPLETED = 2
	BLOCKED = 3  # May require intervention of user, or other agent, or just wait for issue to be resolved
	FAILED = 4


class TaskRole(Enum):
	USER = 0
	AGENT = 1
	OS = 2 # eg. objective roadblocks that need to be resolved


class AgentTask(BaseModel):
	"""Represents a clearly defined goal that needs to be completed by an agent. Task can be completed over many attempts, or not at all. Tasks are persistent between sessions."""
	
	id: str = Field(default_factory=lambda: str(uuid.uuid4()))
	role: TaskRole = Field(default=TaskRole.USER)
	role_id: str = Field(default="User") # eg. user id, agent id
	goal: str # What needs to be done
	status: TaskStatus = Field(default=TaskStatus.NOT_STARTED)
	resolution: Optional[str] = Field(default=None) # What happened with this task
	# TODO: A field for actual result of the task (data?)
	related_messages: List[str] = Field(default_factory=list)
	related_documents: List[str] = Field(default_factory=list)

	def start(self):
		self.status = TaskStatus.IN_PROGRESS

	def complete(self, resolution: str):
		self.status = TaskStatus.COMPLETED
		self.resolution = resolution

	def to_json(self):
		return {
			"id": self.id,
			"goal": self.goal,
			"status": self.status.name,
			"resolution": self.resolution
		}

	def __str__(self):
		string = f"Task Id: {self.id} - {self.goal} - {self.status.name}"
		if self.resolution:
			string += f" - {self.resolution}"
		return string

	def __eq__(self, other):
		if isinstance(other, AgentTask):
			return str(self.id) == str(other.id)
		return False

	def __hash__(self):
		return hash(self.id)


class AgentTaskList(BaseModel):
	"""Manages a collection of agent tasks with methods for adding, finding and filtering tasks"""
	
	tasks: List[AgentTask] = Field(default_factory=list)
	
	def add(self, task: AgentTask) -> bool:
		"""
		Add a task to the list if it doesn't already exist.
		Returns True if task was added, False if it already existed
		"""
		if not self.get_by_id(task.id):
			self.tasks.append(task)
			return True
		return False
	
	def get_by_id(self, task_id: str) -> Optional[AgentTask]:
		"""Find a task by its ID"""
		for task in self.tasks:
			if task.id == task_id:
				return task
		return None
	
	def get_by_status(self, status: TaskStatus) -> List[AgentTask]:
		"""Get all tasks with a specific status"""
		return [task for task in self.tasks if task.status == status]
	
	def get_by_role(self, role: TaskRole) -> List[AgentTask]:
		"""Get all tasks assigned to a specific role"""
		return [task for task in self.tasks if task.role == role]
	
	def get_by_role_id(self, role_id: str) -> List[AgentTask]:
		"""Get all tasks assigned to a specific role ID"""
		return [task for task in self.tasks if task.role_id == role_id]
	
	def remove(self, task_id: str) -> bool:
		"""Remove a task by its ID. Returns True if task was found and removed"""
		task = self.get_by_id(task_id)
		if task:
			self.tasks.remove(task)
			return True
		return False
	
	def __len__(self) -> int:
		return len(self.tasks)
	
	def __iter__(self):
		return iter(self.tasks)
	
	def __getitem__(self, index: int) -> AgentTask:
		return self.tasks[index]

# TODO: Kolejny indeks tasków, który mapuje uuid na integer?