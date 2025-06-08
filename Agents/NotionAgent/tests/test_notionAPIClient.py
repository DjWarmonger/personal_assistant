import pytest
import os
import re
from unittest.mock import AsyncMock, patch, MagicMock
from dotenv import load_dotenv

from operations.notionAPIClient import NotionAPIClient
from operations.blockHolder import BlockHolder
from operations.urlIndex import UrlIndex
from operations.exceptions import HTTPError
from tz_common import CustomUUID

load_dotenv()

@pytest.fixture
def mock_block_holder():
	"""Create a mock BlockHolder for testing."""
	mock_holder = MagicMock(spec=BlockHolder)
	mock_holder.clean_error_message.return_value = {"message": "Test error"}
	return mock_holder

@pytest.fixture
def api_client(mock_block_holder):
	"""Create a NotionAPIClient instance for testing."""
	token = os.getenv("NOTION_TOKEN")
	if not token:
		pytest.skip("NOTION_TOKEN not found in environment")
	return NotionAPIClient(token, mock_block_holder)


@pytest.mark.asyncio
async def test_api_client_initialization(mock_block_holder):
	"""Test that NotionAPIClient initializes correctly."""
	token = "test_token"
	client = NotionAPIClient(token, mock_block_holder)
	
	assert client.notion_token == token
	assert client.page_size == 10  # Default page size
	assert client.headers["Authorization"] == f"Bearer {token}"
	# Check that Notion-Version follows YYYY-MM-DD format
	assert re.match(r"^\d{4}-\d{2}-\d{2}$", client.headers["Notion-Version"])


@pytest.mark.asyncio
async def test_get_page_raw_success(mock_block_holder):
	"""Test successful page retrieval."""
	token = "test_token"
	client = NotionAPIClient(token, mock_block_holder)
	
	mock_response = AsyncMock()
	mock_response.status_code = 200
	mock_response.json = lambda: {"id": "test-page-id", "object": "page"}
	
	with patch('operations.notionAPIClient.AsyncClientManager.wait_for_next_request') as mock_wait, \
		 patch('operations.notionAPIClient.AsyncClientManager.get_client') as mock_get_client:
		
		mock_client = AsyncMock()
		mock_client.get.return_value = mock_response
		mock_get_client.return_value = mock_client
		
		result = await client.get_page_raw("test-page-id")
		
		assert result == {"id": "test-page-id", "object": "page"}
		mock_wait.assert_called_once()
		mock_client.get.assert_called_once_with(
			"https://api.notion.com/v1/pages/test-page-id",
			headers=client.headers,
			timeout=30.0
		)


@pytest.mark.asyncio
async def test_get_page_raw_error(mock_block_holder):
	"""Test page retrieval with HTTP error."""
	token = "test_token"
	client = NotionAPIClient(token, mock_block_holder)
	
	mock_response = AsyncMock()
	mock_response.status_code = 404
	mock_response.json = lambda: {"message": "Page not found"}
	
	with patch('operations.notionAPIClient.AsyncClientManager.wait_for_next_request'), patch('operations.notionAPIClient.AsyncClientManager.get_client') as mock_get_client:
		
		mock_client = AsyncMock()
		mock_client.get.return_value = mock_response
		mock_get_client.return_value = mock_client
		
		with pytest.raises(HTTPError) as exc_info:
			await client.get_page_raw("invalid-page-id")
		
		assert exc_info.value.status_code == 404
		assert exc_info.value.operation == "get_page_raw"


@pytest.mark.asyncio
async def test_get_block_children_raw_with_cursor(mock_block_holder):
	"""Test block children retrieval with pagination cursor."""
	token = "test_token"
	client = NotionAPIClient(token, mock_block_holder)
	
	mock_response = AsyncMock()
	mock_response.status_code = 200
	mock_response.json = lambda: {"results": [], "has_more": False}
	
	with patch('operations.notionAPIClient.AsyncClientManager.wait_for_next_request'), \
		 patch('operations.notionAPIClient.AsyncClientManager.get_client') as mock_get_client:
		
		mock_client = AsyncMock()
		mock_client.get.return_value = mock_response
		mock_get_client.return_value = mock_client
		
		# Create a proper CustomUUID for the cursor
		cursor_uuid = CustomUUID.from_string("12345678-1234-1234-1234-123456789abc")
		result = await client.get_block_children_raw("block-id", start_cursor=cursor_uuid)
		
		assert result == {"results": [], "has_more": False}
		mock_client.get.assert_called_once_with(
			f"https://api.notion.com/v1/blocks/block-id/children?page_size=20&start_cursor={cursor_uuid.to_formatted()}",
			headers=client.headers,
			timeout=30.0
		)


@pytest.mark.asyncio
async def test_search_raw(mock_block_holder):
	"""Test search functionality."""
	token = "test_token"
	client = NotionAPIClient(token, mock_block_holder)
	
	mock_response = AsyncMock()
	mock_response.status_code = 200
	mock_response.json = lambda: {"results": [{"id": "result-1"}]}
	
	with patch('operations.notionAPIClient.AsyncClientManager.wait_for_next_request'), \
		 patch('operations.notionAPIClient.AsyncClientManager.get_client') as mock_get_client:
		
		mock_client = AsyncMock()
		mock_client.post.return_value = mock_response
		mock_get_client.return_value = mock_client
		
		# Create a proper CustomUUID for the cursor
		cursor_uuid = CustomUUID.from_string("87654321-4321-4321-4321-abcdef123456")
		result = await client.search_raw("test query", filter_type="page", start_cursor=cursor_uuid)
		
		assert result == {"results": [{"id": "result-1"}]}
		
		# Verify the payload structure
		call_args = mock_client.post.call_args
		payload = call_args[1]["json"]
		assert payload["query"] == "test query"
		assert payload["filter"]["value"] == "page"
		assert payload["start_cursor"] == cursor_uuid.to_formatted()


@pytest.mark.asyncio
async def test_query_database_raw(mock_block_holder):
	"""Test database query functionality."""
	token = "test_token"
	client = NotionAPIClient(token, mock_block_holder)
	
	mock_response = AsyncMock()
	mock_response.status_code = 200
	mock_response.json = lambda: {"results": [{"id": "db-result-1"}]}
	
	filter_obj = {"property": "Status", "select": {"equals": "TODO"}}
	
	with patch('operations.notionAPIClient.AsyncClientManager.wait_for_next_request'), \
		 patch('operations.notionAPIClient.AsyncClientManager.get_client') as mock_get_client:
		
		mock_client = AsyncMock()
		mock_client.post.return_value = mock_response
		mock_get_client.return_value = mock_client
		
		# Create proper CustomUUIDs
		db_uuid = CustomUUID.from_string("abcdef12-3456-7890-abcd-ef1234567890")
		cursor_uuid = CustomUUID.from_string("fedcba09-8765-4321-fedc-ba0987654321")
		result = await client.query_database_raw(db_uuid, filter_obj=filter_obj, start_cursor=cursor_uuid)
		
		assert result == {"results": [{"id": "db-result-1"}]}
		
		# Verify the payload structure
		call_args = mock_client.post.call_args
		payload = call_args[1]["json"]
		assert payload["filter"] == filter_obj
		assert payload["start_cursor"] == cursor_uuid.to_formatted()


@pytest.mark.asyncio
async def test_initialization_only(mock_block_holder):
	"""Test NotionAPIClient initialization (no async context manager needed)."""
	token = "test_token"
	
	client = NotionAPIClient(token, mock_block_holder)
	assert isinstance(client, NotionAPIClient)
	assert client.notion_token == token


# Integration test (only runs if NOTION_TOKEN is available)
@pytest.mark.asyncio
async def test_real_api_call(api_client):
	"""Test actual API call to Notion (requires valid token and page ID)."""
	page_id = os.getenv("NOTION_LANDING_PAGE_ID")
	if not page_id:
		pytest.skip("NOTION_LANDING_PAGE_ID not found in environment")
	
	# NotionAPIClient doesn't need async context manager, just call the method directly
	try:
		result = await api_client.get_page_raw(page_id)
		assert "id" in result
		assert "object" in result
		assert result["object"] == "page"
	except Exception as e:
		pytest.fail(f"Real API call failed: {e}") 