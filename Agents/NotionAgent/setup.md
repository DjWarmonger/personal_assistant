# NotionAgent Setup

## Requirements
- Python 3.10+
- Conda environment with required packages
- Notion API Token

## Environment Setup
1. Create a conda environment:
   ```
   conda create -n services python=3.10
   conda activate services
   ```

2. Install required packages:
   ```
   pip install langchain langchain-openai langfuse pydantic==1.10.8 pytest pytest-asyncio dotenv flask
   ```

3. Set up environment variables:
   - Create a `.env` file in the NotionAgent directory
   - Add the following variables:
     ```
     NOTION_TOKEN=your_notion_api_token
     NOTION_LANDING_PAGE_ID=your_landing_page_id
     ```

## Directory Structure
After reorganization, the NotionAgent follows this structure:
- `Agent/`: Core agent functionality
- `operations/`: Implementations of operations like Notion API interactions
- `launcher/`: Application entry points
- `tests/`: Unit tests
- `resources/`: Images and other resources

## Running the Agent

### Interactive Chat Mode
Navigate to the project root directory and run:
```
conda activate services
python -m Agents.NotionAgent.launcher.chat
```

### REST Server Mode
To run the agent as a REST API server:
```
conda activate services
python Agents/NotionAgent/launcher/rest_server.py
```

The REST server will be available at:
- Health check: `http://127.0.0.1:8000/health`
- Process endpoint: `http://127.0.0.1:8000/api/v1/process`

#### API Usage Examples
```bash
# Health check
curl http://127.0.0.1:8000/health

# Process request
curl -X POST http://127.0.0.1:8000/api/v1/process \
  -H "Content-Type: application/json" \
  -d '{"input": "Hello, how can you help me?"}'
```

## Testing

### Run All Tests
```
conda activate services
python -m pytest Agents/NotionAgent/tests -v
```

### Run REST Server Tests
```
conda activate services
python -m pytest Agents/NotionAgent/tests/test_rest_server.py -v
```

For detailed testing commands and manual testing procedures, see `.notes/notion-agent-testing-commands.md`.