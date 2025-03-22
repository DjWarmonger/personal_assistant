from dotenv import load_dotenv

from langchain_openai.chat_models import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import JsonOutputParser

from .agentTools import agent_tools

load_dotenv()

wildcard_examples = ",".join([
	"users.*.name",
	"records.*.timestamp.hours",
	"complex.nested.structure.3.complexObject"
])


system_prompt = f"""
You are an AI agent designed to assist with tasks related to JSON document manipulation.
Your goal is to search, modify, add, delete, load, and save JSON documents based on user requests.

<instructions>
You only have access to documents via tools. Assume documents are already loaded and available via tools at conversation start.
</instructions>

<instructions>
By default use working document.
</instructions>

<instructions>
Ask clarifying questions if needed.
</instructions>

<instructions>
If user request is ambiguous, or can be implemented in multiple ways, present both interpretations and ask user to clarify.
</instructions>

<instructions>
For tools that access specific parts of json document, use the wildard path format. examples of paths: {wildcard_examples}. Path can be empty so document root is selected.
</instructions>

<instructions>
You may call multiple tools at once, but DO NOT call tool many times with same arguments.
</instructions>

<instructions>
No tool calls will be considered as finish condition and current message will be returned to the user.
</instructions>

"""
# <instructions>
# Once all tasks are finished (or there are no more tasks to be done), call Respond tool to return the response to the user.
# </instructions>

# <instructions>
# Use complete_task tool to indicate that given task is finished. Finishing all tasks will be considered as completing the assignment.
# </instructions>

# <instructions>
# Ask user for confirmation before saving the JSON document.
# </instructions>

# TODO: Add non-interactive version of the agent

prompt = ChatPromptTemplate.from_messages(
	[
		SystemMessagePromptTemplate.from_template(system_prompt),
		MessagesPlaceholder(variable_name="messages"),
	]
)

llm = ChatOpenAI(
	model="gpt-4o-mini-2024-07-18",
	streaming=True,
	temperature=0.01,
)

json_agent_runnable = prompt | llm.bind_tools(agent_tools)
