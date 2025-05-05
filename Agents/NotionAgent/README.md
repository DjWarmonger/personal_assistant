# NotionAgent

NotionAgent is an AI-powered assistant designed to interact with Notion workspaces programmatically. It enables searching, navigation, content retrieval, and task management in Notion documents through an agent-based architecture.

## Key Features

- **Notion Integration**: Search, retrieve, and navigate Notion content using the Notion API
- **Agent System**: Multi-agent system with specialized roles (Planner, Notion Explorer, Writer)
- **Task Management**: Automated task creation and execution for complex workflows
- **Block Tree Visualization**: Visual representation of Notion page hierarchies
- **Content Caching**: Efficient caching system to minimize API calls
- **Favorites System**: Track and quickly access frequently used Notion pages

## Architecture

The NotionAgent is built with a modular architecture:

```
Agents/NotionAgent/
├── Agent/                     # Core agent functionality
│   ├── agentTools.py          # Tools for agent interactions
│   ├── graph.py               # State machine for agent behavior
│   ├── agents.py              # Agent implementations
│   └── agentState.py          # State management
│
├── operations/                # Notion API operations
│   ├── notion_client.py       # Notion API client
│   ├── blockCache.py          # Caching system
│   ├── blockTree.py           # Tree representation
│   └── index.py               # Page indexing system
│
├── launcher/                  # Application entry points
│   ├── chat.py                # Interactive chat interface
│   └── commandLine.py         # Command-line interface
│
├── tests/                     # Test suite
│
└── resources/                 # Resource files
```

## Agent System

The system consists of three specialized agents working together:

1. **Planner Agent**: Breaks down user requests into actionable tasks for other agents
2. **Notion Agent**: Navigates Notion, retrieves content, and executes operations
3. **Writer Agent**: Synthesizes information from Notion into coherent responses

## Getting Started

See [setup.md](setup.md) for detailed setup instructions.

## Usage Examples

### Basic Query
```
You: Find my notes about Python programming
```

### Document Navigation
```
You: Navigate to my project planning page and summarize the content
```

### Content Aggregation
```
You: Collect all tasks marked as "Important" across my workspace
```

## Contributing

See [TODO.md](TODO.md) for current development priorities and [ALREADY_DONE.md](ALREADY_DONE.md) for completed features.

## License

This project is for personal use only. 