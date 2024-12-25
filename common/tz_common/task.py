from enum import Enum
import uuid

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

class AgentTask:

	"""Represents a clealry defined goal that needs to be completed by an agent. Task can be completed over many attempts, or not at all. Tasks are persistent between sessions."""
	
	id: str
	role: TaskRole
	role_id: str # eg. user id, agent id
	
	related_messages = []
	related_documents = [] # Document may be related to URL, access it indirectly
	status = TaskStatus.NOT_STARTED
	resolution: str | None = None # What happened with this task - it was completed in a specific way, or expired, or nothing had to be done. Also, taks could be invalid from the start
	
	# TODO: Generate role id automagicallywith some method

	def __init__(self, goal: str, role: TaskRole, role_id: str):
		# TODO: UUid may depend on context: https://docs.python.org/3/library/uuid.html#uuid.uuid4
		self.id = str(uuid.uuid4())
		self.goal = goal
		self.role = role
		self.role_id = role_id

	def run(self):
		pass

# TODO: Kolejny indeks tasków, który mapuje uuid na integer?