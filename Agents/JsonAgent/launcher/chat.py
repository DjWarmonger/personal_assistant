import os
import sys
from pathlib import Path

# Enable relative imports when running as a script
if __name__ == "__main__":
	# Add parent directory to path to make this file importable
	current_dir = Path(__file__).parent.absolute()
	project_root = current_dir.parent
	
	if str(project_root) not in sys.path:
		sys.path.insert(0, str(project_root))

from langchain_community.chat_message_histories import ChatMessageHistory

from tz_common.logs import log
# Import directly from Agent package
from Agent.graph import json_agent, langfuse_handler


def chat(loop = True,
		 user_prompt = "",
		 initial_json = None) -> str:
	console_prompt = "You: "
	history = ChatMessageHistory()
	
	# TODO: Type "save" to save the current JSON document to a file
	# TODO: Agent should know that user has to do it manually
	
	user_input = ""
	
	print("Hello! I'm your JSON Agent chatbot. Type 'quit' to exit.")
	while True:
		if user_prompt and not user_input:
			# Only at first run
			user_input = user_prompt
		else:
			user_input = input(console_prompt)
			log.user_silent(user_input)
	
		if user_input.lower() == 'quit':
			break

		if not user_input:
			continue

		history.add_user_message(user_input)

		# Prepare initial state with JSON document if provided
		initial_state = {
			"messages": history.messages,
			"actions": [],
		}
		
		# Add JSON document to initial state if provided
		if initial_json is not None:
			initial_state["initial_json_doc"] = initial_json
			initial_state["json_doc"] = initial_json

		response = json_agent.invoke(
			initial_state,
			config={"callbacks": [langfuse_handler]}
		)

		# Store all fields from AgentState and JsonAgentState
		current_state = {
			# Common AgentState fields
			"messages": response.get("messages", []),
			"initialPrompt": response.get("initialPrompt", []),
			"unsolvedTasks": response.get("unsolvedTasks", set()),
			"completedTasks": response.get("completedTasks", set()),
			"actions": response.get("actions", []),
			"toolResults": response.get("toolResults", []),
			"recentResults": response.get("recentResults", []),
			
			# JsonAgentState specific fields
			"initial_json_doc": response.get("initial_json_doc", {}),
			"json_doc": response.get("json_doc", {}),
			"final_json_doc": response.get("final_json_doc", {})
		}
		
		# Get the assistant's response
		assistant_response = response["messages"][-1].content
		log.ai("Assistant: \n", assistant_response)
		
		history = ChatMessageHistory()
		for message in response["messages"]:
			history.add_message(message)

		if not loop:
			return assistant_response


if __name__ == "__main__":
	chat() 