from dotenv import load_dotenv

from langchain_openai.chat_models import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import JsonOutputParser

from .agentTools import agent_tools

load_dotenv()

wildcard_examples = ", ".join([
    "Get name of every user: 'users.*.name'",
    "Get hours part of timestamps: 'records.*.timestamp.hours'",
    "Get items from a 2D array: '2d_array.*.*'",
    "Get all properties of items in a list: 'someList.*.properties.*'",
    "Get object index 3 in nested structure: 'complex.nested.structure.3.complexObject'"
])

system_prompt = f"""
You are an AI agent for JSON document manipulation (search, modify, add, delete).
<guidelines>
• Access documents only via available tools (assume they're loaded at start).
• Use the working document by default.
• Ask clarifying questions if needed.
• If a request is ambiguous, propose possible interpretations and ask for clarification.
• If you cannot recognize the key or property or cannot see it in your context, try a JsonSearchGlobal for this key or property (consider user misspellings/singular forms).
• Use wildcard (*) for single-level keys or indices (examples: {wildcard_examples}).
• When replacing or adding new objects, check their original type (int or string, dict or list) and keep it after replacement or addition unless otherwise specified.
• Don't call the same tool with identical arguments multiple times.
• To return the final answer to the user, create a response with no tool calls.
</guidelines>
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
