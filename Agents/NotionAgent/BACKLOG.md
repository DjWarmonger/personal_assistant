# Fix bugs

## 404 on NotionQueryDatabase

```
Querying Notion database... 4fa780c8df7746ff83500cd7d504c3d7
Start cursor: None
filter:{'property': 'Date', 'date': {'equals': '2024-06-06'}}
404{'status': 404, 'code': 'object_not_found', 'message': 'Could not find database with ID: 4fa780c8-df77-46ff-8350-0cd7d504c3d7. Make sure the relevant pages and databases are shared with your integration.'}
```

* Actually: this is not a database, but a block (list of actual TODO items)

- TODO: Get it from cache and check if it's a database.

It's tricky since cache keys are prefixed with type of the object.

- Make sure Agent doesn't pick db as a block
- Make sure Client doesn't return db as a block


## ValueError: No block info in context

Occurs with 'Add this page to favourites' test. Writer is activated without need, no block info in context.

* Incorrect task generated for Writer:

> 'role': 'AGENT', 'role_id': 'WRITER', 'goal': "Summarize and confirm to the user that the page 'Integracja z Notion' has been successfully added to favourites. Ensure the response is clear and user-friendly.

## Task is already completed in Notion Agent

> Call tool failed: (AgentAction(id='OXoijUjaTjKoIGp1bbD13Pf6', created_at=datetime.datetime(2025, 5, 17, 15, 5, 44, 210762, tzinfo=datetime.timezone.utc), task_id='', agent_id='', description="complete_task (OXoijUjaTjKoIGp1bbD13Pf6) with args: {'task_id': 'b488f64a-eab5-4c77-9b34-de0f9cbfb53e', 'status': 'completed', 'resolution': 'Page TODO dzień added to favourites'}", related_messages=[], related_documents=[], status=<ActionStatus.IN_PROGRESS: 1>, resolution=None), 'Task is already completed: b488f64a-eab5-4c77-9b34-de0f9cbfb53e')

- Check what kinds of tasks are generated
   - What agent ID they have
   - Which agent are they passed to?
- Check what Notion Agent can do once task is completed
- Check what Planning Agent can do once task is completed

## Useless error message for empty block tree

> blockTree is empty in notion state at response_check

- blockTree is not needed when we're just adding page to favourites

# Code Improvements

Reuse timeline builder from call_json_agent to build timeline for other agents

# Optimizations

- Remove duplicated "plain_text" field if "content" is present

# Features
- Add support for editing Notion pages and blocks
- Implement better task management features
   - Explicit delegation to other agents
- Create a dashboard for monitoring agent activity
- Add webhooks support for real-time updates
- Improve search functionality with more filters

# Integration
- Add YouTube integration
- Create integration with n8n
- Implement OAuth for easier authentication

# Future Ideas
## Agent Features
- Add background agent for generating page maps and summaries
- Implement agent for managing page layouts and references
- Add multi-language support with focus on Polish

# Scenarios to Support
- Information search and aggregation
- Index editing
- Information editing
- Autonomous actions
- Task management and TODO list maintenance
- Content organization and cleanup

# Marimo Dashboard

- Store prompts in database, with various properties

