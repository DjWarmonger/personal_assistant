from datetime import datetime, timezone

from langchain_core.messages import BaseMessage

def add_timestamp(message: BaseMessage):
	message.response_metadata["timestamp"] = datetime.now(timezone.utc)

