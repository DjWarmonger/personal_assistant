from langchain_community.chat_message_histories import ChatMessageHistory

from tz_common.logs import log
from plannerGraph import planner_runnable
from graph import notion_agent, langfuse_handler


def chat(loop = True, user_prompt = "") -> str:

	console_prompt = "You: "

	history = ChatMessageHistory()
	
	print("Hello! I'm your chatbot. Type 'quit' to exit.")
	while True:

		# TODO: Create another utility with input() in green color

		if user_prompt:
			user_input = user_prompt
		else:
			user_input = input(console_prompt)
			log.user_silent(user_input)
	
		if user_input.lower() == 'quit':
			break

		if not user_input:
			continue

		history.add_user_message(user_input)

		# FIXME: Langfuse cannot handle dicts

		response = planner_runnable.invoke(
			{
				"messages": history.messages,
				"actions": [],
			},
			config={"callbacks": [langfuse_handler]}
		)

		log.ai("Assistant: \n", response["messages"][-1].content)

		# FIXME: Render \n as actual new lines
		# FIXME: Render \t
		#log.ai("Assistant: \n", response["messages"][-1].content)
		
		history = ChatMessageHistory()
		for message in response["messages"]:
			history.add_message(message)

		if not loop:
			#return "Task list retrieved successfully"
			return response["messages"][-1].content




if __name__ == "__main__":
	chat()
