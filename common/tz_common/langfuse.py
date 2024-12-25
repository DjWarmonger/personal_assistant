import os
import time
from langfuse.callback import CallbackHandler

from dotenv import load_dotenv  

def create_langfuse_handler(user_id: str, session_id: str = ""):

	load_dotenv(override=False)

	if not session_id:
		session_id = time.strftime("%Y-%m-%d_%H-%M-%S")

	langfuse_handler = CallbackHandler(
		secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
		public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
		host=os.getenv("LANGFUSE_HOST"),
		user_id=user_id,
		session_id=session_id
	)

	return langfuse_handler
