## Notion Official MCP Server
**Repository:** `makenotion/notion-mcp-server`

**Description:**
Official open-source MCP server by Notion. Bridges to the Notion API for searching content, querying databases, managing pages, and handling comments via a standardized interface. Provides full visibility into all API calls (using Notion's v1 JSON API) and flexibility to customize enabled capabilities.

**MCP Features (Context & Tools):**
- Exposes Notion workspace data as MCP tools (e.g. search, list databases, get/update page, add comment)
- Supports reading and writing of pages, databases, and comments via Notion API endpoints
- No unofficial scraping – uses only official API calls
- Compatible with MCP spec 1.x and any MCP-compliant client

**Agent Capabilities & Use Cases:**
- Lets AI agents retrieve and update content in Notion
- Common use cases include knowledge-base querying (agent can search pages or databases by title)
- Content creation (e.g. add a page or database entry)
- Commenting or annotating Notion docs
- Suitable for team documentation assistants, project trackers, etc., in Cursor or Claude
- Deletion of entire databases is intentionally disallowed for safety

**Setup (Local Installation):**
Installable via npm or Docker. For example, add to Cursor's `.mcp.json` with an `npx` command to run the package (or use the official Docker image) and provide the Notion integration token via env var. No cloud services required aside from Notion API.

**Community & Adoption:**
Widely adopted with ~2.2k⭐ on GitHub. As the official solution, it's frequently updated and documented by Notion (released April 2025). Many community guides and Notion's docs reference this server, making it a default choice for Notion–LLM integration.

**Performance Notes:**
Reliable and comprehensive. Responses use verbose JSON (the standard Notion API schema), which can consume more tokens – the official docs note that the self-hosted server is less token-efficient than Notion's hosted beta (which uses a compact Markdown format). Still, it handles large content well, and you can self-host to control memory and rate limits. No built-in caching or special optimizations, but standard Node/TypeScript performance is adequate.

---

## Notion MCP by suekou
**Repository:** `suekou/mcp-notion-server`

**Description:**
Community-driven MCP server (TypeScript) enabling full Notion workspace integration. It allows AI assistants to list, read, create, and update Notion pages and databases via official API calls. Additionally, it can convert Notion content to Markdown to reduce context size for the LLM, optimizing token usage.

**MCP Features (Context & Tools):**
- Provides a comprehensive set of MCP tools covering most of Notion's API
- Page retrieval and editing, database query/creation, block operations (append, delete, etc.)
- Search functionality and user info and comments
- All tools can return JSON (default) or a concise Markdown representation (when `NOTION_MARKDOWN_CONVERSION=true`)
- Supports optional tool whitelisting to run in read-only or limited modes

**Agent Capabilities & Use Cases:**
- Equips an AI agent to serve as a Notion content manager or assistant
- Agent can search the workspace for relevant pages, answer questions from page content (using Markdown output for efficiency)
- Create or update pages (e.g. documenting plans or code snippets)
- Add comments or list users
- Suitable for dynamic knowledge bases, note-taking assistants, or task automation in Notion
- Broad toolset and format flexibility make it useful in developer workflows where context size is a concern

**Setup (Local Installation):**
Available as an npm package. Simply add it to the MCP config in Cursor/Claude with an `npx -y @suekou/mcp-notion-server` command, setting the `NOTION_API_TOKEN` env var to your integration key. Requires Node 18+. No external services needed. (Markdown mode is off by default but can be enabled via env var.)

**Community & Adoption:**
Highly popular with ~757⭐ on GitHub. One of the earliest and most-used Notion MCP servers (est. 89k+ total downloads). The project is open-source (MIT) and has active community engagement (issues and forks for improvements). Often recommended for its reliability and token-efficiency feature.

**Performance Notes:**
Emphasizes token efficiency – the optional Markdown conversion can significantly shrink output size, allowing more content in the model's context. Response generation and API calls are handled asynchronously and are as fast as Notion's API allows. No special caching, but supports limiting enabled tools to reduce unnecessary overhead. Implemented in TypeScript using Notion's SDK, so performance is comparable to official server, with extra processing when markdown mode is enabled (which is generally minor compared to network latency).

---

## Notion MCP by Yaroslav Boiko
**Repository:** `awkoy/notion-mcp-server`

**Description:**
A production-ready Node/TypeScript MCP server providing a complete bridge to Notion for AI assistants. It offers a full suite of tools to read, create, and modify Notion content through natural language. Notably, it introduces batch operations to handle multiple Notion actions in a single request for efficiency. Recent versions also added support for comments and user management (in addition to pages, databases, and blocks).

**MCP Features (Context & Tools):**
- Implements a wide range of MCP tools with some consolidated endpoints for efficiency
- Supports bulk appending or updating of blocks in one call
- Combined actions on pages (create/search/update in one tool)
- Includes tools for page CRUD (and archival/restore), block CRUD, database CRUD, search
- Commenting (get/add comments), and user info (list users, get user/bot profile)
- Fully MCP-compliant and tested with multiple clients (Cursor, Claude, Cline, etc.)

**Agent Capabilities & Use Cases:**
- Enables advanced Notion automation via AI
- Documentation maintenance (the agent can batch-add multiple entries or update many blocks at once)
- Project management (create project pages and sub-tasks in one go)
- Content analysis (fetch and aggregate info from many pages)
- The batch operations feature allows an agent to plan and execute complex edits more efficiently (fewer round trips)
- Also suitable for Q&A or summarization across pages, with search and multi-fetch capabilities

**Setup (Local Installation):**
Installable via npm (`notion-mcp-server` on NPM). You can run it with `npx` in a Cursor `mcp.json` config; just supply your Notion API token (and optionally a target page ID if needed) in the environment. Supports Docker as well. No external API keys required beyond the Notion integration token.

**Community & Adoption:**
Active community project with ~120⭐ on GitHub and growing (released Mar 2025). It's well-regarded for its completeness and "batteries-included" approach. Estimated ~2.6k downloads in the first months. The developer actively updates it with new Notion features (e.g. comments, users) and provides detailed documentation.

**Performance Notes:**
Optimized for speed and context efficiency. Batch operations allow combining multiple tool calls into one, reducing API latency overhead. The server uses the official Notion SDK with input validation (Zod) to ensure correct and safe operations. It handles large data sets (e.g. listing many users or blocks) with streaming or pagination under the hood. Overall memory usage is modest (Node.js) and the design avoids unnecessary token bloat – responses can be targeted (e.g. specific fields or batched results) to keep them concise.

---

## Notion MCP by Chase Cabanillas
**Repository:** `ccabanillas/notion-mcp`

**Description:**
A Python-based MCP server for Notion that supports common content management operations. It provides a standardized interface to list and query databases, retrieve and update pages, and search the workspace via Notion's API. This server was built to integrate with Claude Desktop and Cursor as a self-hosted alternative to the official server.

**MCP Features (Context & Tools):**
- Implements core MCP tools for Notion: listing databases, querying database entries
- Fetching page content (and children blocks), creating or updating pages
- Global workspace search
- Interfaces with Notion API v2022-02-22, returning JSON data
- Does not include advanced features like comments or user listing – focuses on pages and databases
- Fully asynchronous I/O (using `httpx`), which allows concurrent retrieval of content for efficiency
- Compatible with MCP v1.6.0 spec

**Agent Capabilities & Use Cases:**
- Allows an AI agent to dynamically retrieve and modify content in Notion
- Agent in Cursor could pull relevant notes or specs from Notion pages to assist coding
- Update a Notion database of issues/tasks as you instruct it
- Suited for general wiki/documentation assistants or project notes management
- Because it lacks comment and user tools, it's mainly for content CRUD and searching within Notion
- Covers most developer knowledge base use cases

**Setup (Local Installation):**
Clone the repo and install (`pip install -e .`) in a Python 3.10+ virtual env. Define your `NOTION_API_KEY` in a `.env` file. Run the server with `python -m notion_mcp`. Then configure Cursor/Claude to spawn this server (point to the Python interpreter and module in config). Entirely self-hosted; just needs your Notion token.

**Community & Adoption:**
Moderate adoption with ~105⭐ on GitHub. It's a newer project (Dec 2024) referenced by early MCP users; relatively fewer downloads (on the order of a few thousand) compared to Node alternatives. Users appreciate its simplicity and Python's ease of customization. Community feedback notes it works out-of-the-box with Claude Desktop and Cursor with minimal fuss.

**Performance Notes:**
Good for small-to-medium workloads. The use of async calls and Pydantic models ensures non-blocking performance and type-checked reliability. Python adds some overhead vs Node, but network calls dominate latency (Notion API). Memory footprint is low; however, large pages will be loaded into memory as JSON. No special token optimization (output is raw JSON), so very large page dumps could approach token limits in some cases. Overall, it's stable and fast enough for typical Notion content sizes.

---

## Notion Todo MCP (Dan Hilse)
**Repository:** `danhilse/notion_mcp`

**Description:**
A lightweight MCP server focusing on a personal todo list in Notion. It was designed for a single Notion database with a simple schema (Task, Due date, Done checkbox) to allow AI (Claude or Cursor) to read and manage tasks. Essentially a niche example of using MCP for task management in Notion.

**MCP Features (Context & Tools):**
- Provides a few specialized MCP tools corresponding to todo-list operations
- Adding a new todo (creates a page in the todo database)
- Listing all todos or filtering by "today" vs "later"
- Marking a task as complete (updates a checkbox property)
- Uses standard Notion API calls (querying the specific database, updating page properties for completion, etc.)
- Tool definitions are hard-coded for the expected database structure, which means it's not generic beyond the intended use

**Agent Capabilities & Use Cases:**
- Enables an AI agent to interact with a Notion to-do list in natural language
- You can ask, "What are my tasks for today?" and the agent (Claude/Cursor) will use this server to query the Notion todo database and return the list
- You can say "Add a task for later: update documentation," and the agent will create a new page in the todo list
- Useful for personal productivity assistants
- Because it's tailored to one database, it's not meant for general content queries or wiki-style knowledge retrieval

**Setup (Local Installation):**
Python 3.10+ project. Clone the repo and install the package (`pip install -e .`). Set up a Notion integration and share a specially structured "Todo" database with it (with specific fields "Task", "When", "Checkbox"). Provide the integration token and the database's ID in a `.env` file. Run with `python -m notion_mcp`. Then add this server to Cursor's MCP config (pointing to the Python executable and module).

**Community & Adoption:**
~184⭐ on GitHub. Gained attention as an early demo (Nov 2024) of MCP with Notion. Many have tried it as a quick win to connect Claude to Notion tasks (even Notion's official docs credit it as inspiration). Its user base is mostly individuals testing AI task management. For broader adoption, users would need to modify it for their own database schemas.

**Performance Notes:**
Very lightweight and focused. Handles only one small database, so memory and speed are not an issue (typical queries or inserts complete in a fraction of a second). The simplicity means minimal overhead – no extra formatting or large JSON dumps, just the fields needed for tasks. However, its narrow scope is a limitation: it cannot utilize multiple CPUs or handle diverse data without code changes. It's best viewed as a reference implementation or quick personal tool rather than a scalable enterprise solution.

---

## SystemPrompt Notion MCP
**Repository:** `systemprompt-mcp-notion` by Ejb503

**Description:**
A high-performance MCP server (TypeScript) from the SystemPrompt project, integrating Notion into AI workflows. It allows AI agents to interact with Notion pages and databases through MCP, including reading, searching, creating, and updating content. (It also supports Notion comments.) This server requires an API key from SystemPrompt (a free developer platform) in addition to a Notion API token.

**MCP Features (Context & Tools):**
- Implements standard Notion API tool interfaces
- Agents can query databases, retrieve page content, create or edit pages with rich text
- Search the workspace functionality
- Supports MCP "sampling" – meaning the agent can generate and send content chunks for Notion (used for creating/updating pages) via the MCP protocol extension
- Error handling and logging are robust (extensive Jest test coverage)
- Essentially mirrors much of the official server's functionality, with the addition of SystemPrompt's integration hooks

**Agent Capabilities & Use Cases:**
- Suitable for AI agents that need to write into Notion in a controlled way
- An agent could take meeting notes (the model generates text which the server then inserts as a Notion page via the sampling tool)
- Covers typical use cases like content retrieval and workspace search as well
- Because it's part of the SystemPrompt ecosystem, it's intended to plug into their MCP client or Claude Desktop with minimal config
- Enables two-way Notion automation in IDEs or chat interfaces

**Setup (Local Installation):**
Distributed via npm (`systemprompt-mcp-notion`). You add it to your MCP config calling `npx systemprompt-mcp-notion` (or install it locally and run the built JS). **Note:** You must obtain a free `SYSTEMPROMPT_API_KEY` from systemprompt.io and set it, along with your `NOTION_API_KEY`, in the environment. After that, it runs locally; the SystemPrompt key is used for authentication/telemetry with their platform.

**Community & Adoption:**
Low to moderate adoption – ~19⭐ on GitHub. It's a newer entry (Jan 2025) and somewhat niche due to the extra account requirement. Some developers in the SystemPrompt community use it for Claude Desktop integration. Outside of that, most opt for the official or other community servers. The project is open-source (MIT) and welcomes contributions, but community feedback is limited so far (no major issues reported).

**Performance Notes:**
Described as "high-performance" by its authors, it's built with efficiency in mind: TypeScript for type safety and speed, careful error handling, and the ability to create content via the sampling interface (which can streamline page writes). In practice, its speed is comparable to other Node-based servers – primarily constrained by Notion API latency. It does not offer the token-saving Markdown mode, so outputs are JSON. Memory use is minimal and on par with typical Node apps. One consideration is the dependency on the SystemPrompt service (for the API key); however, during runtime the heavy work (Notion data fetching) is done locally.
