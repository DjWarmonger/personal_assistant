from datetime import datetime, timezone

from langchain_core.messages import BaseMessage, AIMessage

def add_timestamp(message: BaseMessage):
	message.response_metadata["timestamp"] = datetime.now(timezone.utc)


def create_current_time_message() -> AIMessage:
	"""Create an AI message that informs the agent about the current time."""
	current_time = datetime.now(timezone.utc)
	formatted_time = current_time.strftime("%Y-%m-%d %H:%M:%S UTC")
	
	content = f"Current time is {formatted_time}"
	
	message = AIMessage(content=content)
	
	return message

