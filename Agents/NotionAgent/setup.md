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
   pip install langchain langchain-openai langfuse pydantic==1.10.8 pytest pytest-asyncio dotenv
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
Navigate to the project root directory and run:
```
conda activate services
python -m Agents.NotionAgent.launcher.chat
```

## Testing
To run tests:
```
conda activate services
python -m pytest Agents/NotionAgent/tests
```