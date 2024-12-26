from dotenv import load_dotenv
import os

from langchain_openai.chat_models import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, MessagesPlaceholder

from agentTools import agent_tools

load_dotenv()

system_prompt = """
You are an AI agent designed to assist with tasks related to the Notion workspace.
Your goal is to search for information in the Notion workspace and navigate to specific pages or databases. Explore children blocks of visited pages. Focus on insightful content rather than page details.

URLS:
You will only receive URLs in the form of integer indexes, as is {{"url": index}}. Whenever you need to output an URL, you MUST print this placeholder form instead: [[index]]. Example markdown:
[Link description]([[index]])

{can_ask_questions}

When you're finished, add "TASK_COMPLETED" to the end of your response. If you encounter error or obstacle blocking your successful completion of the task, add "TASK_FAILED" to the end of your response.

{can_call_human}
"""

ask_prompt = """Ask clarifying questions as needed. Mark question with 'AGENT_QUESTION'.""" if os.getenv("CAN_ASK_QUESTIONS") == "true" else ""

human_prompt = """If your problem requires human intervention, respond with "HUMAN_FEEDBACK_NEEDED".""" if os.getenv("CAN_CALL_HUMAN") == "true" else ""

prompt = ChatPromptTemplate.from_messages(
	[
		# TODO: Should it add any messages here?
		SystemMessagePromptTemplate.from_template(system_prompt).format(can_ask_questions=ask_prompt, can_call_human=human_prompt),
		MessagesPlaceholder(variable_name="messages"),
	]
)

llm = ChatOpenAI(
	#model="gpt-4o",
	#model="gpt-4o-mini", # Mini does not handle tools with multiple arguments
    model="gpt-4o-mini-2024-07-18",
	streaming=True,
	temperature=0.01,
)

notion_agent_runnable = prompt | llm.bind_tools(agent_tools)