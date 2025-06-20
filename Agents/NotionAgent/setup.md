# NotionAgent Setup

## Requirements
- Python 3.10+
- UV package manager
- Notion API Token

## Environment Setup
1. Install UV package manager (if not already installed):
   ```
   pip install uv
   ```

2. Create and activate the UV virtual environment:
   ```
   uv venv .venv_uv_tz
   .\.venv_uv_tz\Scripts\activate  # Windows
   # or
   source .venv_uv_tz/bin/activate  # Linux/Mac
   ```

3. Install dependencies:
   ```
   uv pip install -r requirements.txt
   uv pip install -e common/src  # Install tz_common
   uv pip install -e .           # Install NotionAgent
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
.\.venv_uv_tz\Scripts\activate  # Windows (or source .venv_uv_tz/bin/activate on Linux/Mac)
python -m Agents.NotionAgent.launcher.chat
```

### REST Server Mode
To run the agent as a REST API server:
```
.\.venv_uv_tz\Scripts\activate  # Windows (or source .venv_uv_tz/bin/activate on Linux/Mac)
python Agents/NotionAgent/launcher/rest_server.py
```

### Docker Mode (Recommended for Production)
To run the agent using Docker with the UV-based container:
```
# Build and run with docker compose
docker compose -f Agents/NotionAgent/docker_compose.yaml up -d

# Check status
docker ps

# View logs
docker logs notion-rest-server

# Stop
docker compose -f Agents/NotionAgent/docker_compose.yaml down
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
.\.venv_uv_tz\Scripts\activate  # Windows (or source .venv_uv_tz/bin/activate on Linux/Mac)
python -m pytest Agents/NotionAgent/tests -v
```

### Run REST Server Tests
```
.\.venv_uv_tz\Scripts\activate  # Windows (or source .venv_uv_tz/bin/activate on Linux/Mac)
python -m pytest Agents/NotionAgent/tests/test_rest_server.py -v
```

### Docker Health Check
```
# Test the containerized version
docker compose -f Agents/NotionAgent/docker_compose.yaml up -d
curl http://localhost:8000/health
docker compose -f Agents/NotionAgent/docker_compose.yaml down
```

For detailed testing commands and manual testing procedures, see `.notes/notion-agent-testing-commands.md`.