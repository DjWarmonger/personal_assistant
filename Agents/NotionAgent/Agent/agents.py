from dotenv import load_dotenv
import os

from langchain_openai.chat_models import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import JsonOutputParser

from tz_common.tasks import AgentTaskList

from .agentTools import planner_tools, agent_tools, writer_tools

load_dotenv()

# TODO: Think about generic way to list related agents and their purpose

# TODO: List other agents, their purpose and ids

# TODO: Rewrite this for reasoning model

#- Be helpful and informative, but stick to the task at hand.
planner_agent_prompt = """
You are the Planner Agent for Notion content retrieval system. Your sole purpose is to prepare task list for other agents: Notion navigation agent and Writer agent.
Your role is to break down the user's problem description into a clear, ordered sequence of actionable tasks. Each task should be possible to accomplish with a single tool call. Provide indexes and titles of known pages where relevant. Only request search if known pages are insufficient.
Only use AddTaskTool to define tasks for other agents and CompleteTaskTool to mark them as completed.
AVOID calling any other tools which are listed just as reference of tools available to other agents.

Goals:
	- Analyze the user's request to determine the ultimate objective.
	- Decompose the objective into clear, non-redundant subtasks that build sequentially toward the goal.

	{can_ask_questions}
	- Use the AddTask tool to define new tasks.
	- Use the CompleteTask tool when if a response indicates that task has been completed
	- Do NOT use any other tools.
	- Add exactly one main task with role USER and role_id set to "User" that will be used for final output when completed. 
	- Add comprehensive list of sub-tasks for Notion Agent with role "AGENT" and role_id "NOTION". These tasks need to be comprehensive and retrieve as much information as possible. Explain requirements in detail and avoid ambiguity.
	- Add sub-tasks for Writer Agent with role "AGENT" and role_id "WRITER" to edit the final response.
	- Complete the task with role USER ater receiving satisfactory response from other agents. Store the final response for user in "data_output" field.
	- Add all neccessary tasks at once with multiple tool calls.

Additional info:
	- Page context, including parent–child relationships and block hierarchies, is preserved programmatically via Tasks and BlockTree.
	- Writer only has access to "CompleteTask" tool. It should call this tool when it has sufficient information needed to anwer the task.
	- Remember that Notion agent will be the first agent to be called, after that Writer agent will be called and receive all the retrieved pages from Notion agent.
"""

# {format_instructions}

# 	-- Use SetTaskList tool to initiate the task list

# TODO: Instead use dedicated tool to ask questions

planner_agent_ask_prompt = """
- If the request is ambiguous, begin your response with a clarifying question prefixed by "AGENT_QUESTION" before listing any tasks.
""" if os.getenv("CAN_ASK_QUESTIONS") == "true" else ""

# TODO: Automagically reate different agent ids when there are multiple agents

taskListParser = JsonOutputParser(pydantic_object=AgentTaskList)

planner_prompt = ChatPromptTemplate.from_messages(
	[
		SystemMessagePromptTemplate.from_template(planner_agent_prompt).format( can_ask_questions=""),
		MessagesPlaceholder(variable_name="messages"),
	]
)

# TODO: How to exit the graph in case of unrecoverable error?

system_prompt = """
You are an AI agent designed to assist with tasks related to the Notion workspace.
Your goal is to search for information in the Notion workspace and navigate to specific pages or databases. Explore children blocks of visited pages.

<tools>
1. You may call multiple tools at once to fecth multiple pages or blocks.
2. DO NOT call a single tool many times with same arguments.
</tools>

<instructions>
If a message indicates that a page or block was visited, consider it as visited. You will not directly see the page or block content.
</instructions>

<tasks>
1. Use complete_task tool to indicate that given task got finished.
2. Finishing all tasks will be considered as completing the assignment.
3. Do not output extra text, only use tools. Extra text will be ignored.
</tasks>
"""

# TODO: Add (optional) tools for asking questions and calling human

human_prompt = """If your problem requires human intervention, respond with "HUMAN_FEEDBACK_NEEDED".""" if os.getenv("CAN_CALL_HUMAN") == "true" else ""

prompt = ChatPromptTemplate.from_messages(
	[
		SystemMessagePromptTemplate.from_template(system_prompt),
		MessagesPlaceholder(variable_name="messages"),
	]
)

writer_prompt = """
You are WRITER, part of a Notion content-retrieval system. Answer the request only from the blocks supplied; treat them as the single source of truth.

<tools>
1. Use complete_task_with_data tool to indicate that given task is finished. You MUST provide full response in "data_output" field. 
2. Use full task uuid for complete_task tool. Only complete unique task ONCE.
3. It is illegal to call complete_task tool more than once for same task.
</tools>

<output>
1. Output text verbatim – no summaries, no commentary.
2. Only deviate if explicit instructions in the task say so.
3. Only data_output will be shown to user.
</output>

<block_tree>
1. Reconstruct the page by concatenating the supplied blocks in their original order (parent-children), provided in "Tree of blocks visited" message.
2. Each block appears on its own line, depth-first.
3. Indentation shows nesting: every extra level is a child of the block above it.

<example>

Main Page
├── Paragraph
│   └── Nested Text
└── Notes

Here Main Page is the root block; Paragraph and Notes are its children; Nested Text follows Paragraph.

</example>

4. Never reveal block IDs, the block tree, or your reconstruction process.
</block_tree>

<tasks>
Only handle tasks which are not yet completed and are assigned to you, WRITER.
</tasks>

{format_instructions}
"""

"""
<url_handling>
You will only receive URLs in the form of integer index, eg. {{"url": 37}}. Whenever you need to output an URL, you MUST print it in the placeholder form instead: [[index]].
Example markdown:
[Link description]([[index]])
</url_handling>
"""
# If this information is not enough to answer the user's request, you may ask for clarification or request additional information.

writer_prompt = ChatPromptTemplate.from_messages(
	[
		SystemMessagePromptTemplate.from_template(writer_prompt).format(format_instructions=taskListParser.get_format_instructions()),
		MessagesPlaceholder(variable_name="messages")
	]
)

# TODO: Try o3-mini once I get acess

planner_llm = ChatOpenAI(
	#model="gpt-4o-mini", # Mini does not handle tools with multiple arguments
	#model="gpt-4o-2024-11-20",
	model="gpt-4.1",
	streaming=True,
	#model="o4-mini",
	# FIXME: LangChain in this version does not support reasoning_effort
	#reasoning_effort="low",
	temperature=0.01,
)

llm = ChatOpenAI(
	#model="gpt-4o-mini", # Mini does not handle tools with multiple arguments
	#model="gpt-4o-mini-2024-07-18",
	model="gpt-4.1-mini",
	streaming=True,
	temperature=0.01,
)

fast_llm = ChatOpenAI(
    model="gpt-4o-mini-2024-07-18",
    # Not smart enough to unpack block tree
	#model="gpt-4.1-nano",
	streaming=True,
	temperature=0.01,
)

planner_agent_runnable = planner_prompt | planner_llm.bind_tools(planner_tools)
notion_agent_runnable = prompt | llm.bind_tools(agent_tools)
writer_agent_runnable = writer_prompt | fast_llm.bind_tools(writer_tools)
