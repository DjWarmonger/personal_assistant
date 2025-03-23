import os
import sys
import json
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
from .commandHandler import JsonAgentCommandHandler


def chat(loop = True,
		 user_prompt = "",
		 initial_json = None) -> str:
	console_prompt = "You: "
	history = ChatMessageHistory()
	
	# Create command handler for JSON Agent
	cmd_handler = JsonAgentCommandHandler()
	
	user_input = ""
	
	# Initialize current_state as empty dict
	current_state = {}
	
	print("Hello! I'm your JSON Agent chatbot. Type 'quit' to exit.")
	print("Type 'help' or '?' for available commands.")
	while True:
		if user_prompt and not user_input:
			# Only at first run
			user_input = user_prompt
		else:
			user_input = input(console_prompt)
			log.user_silent(user_input)
		
		# Handle commands by passing the full current_state
		command_result = cmd_handler.handle_command(user_input, current_state=current_state)
		if command_result == 'quit':
			break
		elif command_result is True:
			continue
		elif isinstance(command_result, dict):
			# Update our current_state with the result from the command
			current_state = command_result
			continue
			
		if not user_input:
			continue

		history.add_user_message(user_input)

		# Prepare initial state with JSON document if provided
		initial_state = {
			"messages": history.messages,
			"actions": [],
		}
		
		# Add JSON document to initial state if providedn
		if initial_json is not None:
			initial_state["initial_json_doc"] = initial_json
			initial_state["json_doc"] = initial_json

		response = json_agent.invoke(
			current_state if current_state else initial_state,
			config={"callbacks": [langfuse_handler]}
		)

		# Update current_state from response
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