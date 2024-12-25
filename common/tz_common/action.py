from enum import Enum
import uuid

class ActionStatus(Enum):
	NOT_STARTED = 0
	IN_PROGRESS = 1
	COMPLETED = 2
	# Action cannot be blocked, it is either completed immediately or failed
	FAILED = 4
	

class AgentAction:

	"""Represents a single attempt to handle a task, like calling a tool or answering the question directly. If action fails, it is gone forever. Further attempts will need to spawn new action."""
	
	id: str
	task_id: str # Task that this action is trying to solve
	agent_id: str # Agent that is performing this action. Can be empty if we asume there's only one agent
	
	related_messages = []
	related_documents = [] # Document may be related to URL, access it indirectly
	status = ActionStatus.NOT_STARTED
	resolution: str | None = None # What happened with this task - it was completed in a specific way, or expired, or nothing had to be done. Also, taks could be invalid from the start
	
	# TODO: Generate role id automagicallywith some method

	def __init__(self, goal: str, agent_id: str= "", task_id: str = ""):
		# TODO: UUid may depend on context: https://docs.python.org/3/library/uuid.html#uuid.uuid4
		self.id = str(uuid.uuid4())
		self.goal = goal
		self.agent_id = agent_id
		self.task_id = task_id

	def run(self):
		pass

# TODO: Kolejny indeks tasków, który mapuje uuid na integer?