import pytest
import os
import re
from unittest.mock import AsyncMock, patch
from dotenv import load_dotenv

from operations.notionAPIClient import NotionAPIClient

load_dotenv()

@pytest.fixture
def api_client():
	"""Create a NotionAPIClient instance for testing."""
	token = os.getenv("NOTION_TOKEN")
	if not token:
		pytest.skip("NOTION_TOKEN not found in environment")
	return NotionAPIClient(token)


@pytest.mark.asyncio
async def test_api_client_initialization():
	"""Test that NotionAPIClient initializes correctly."""
	token = "test_token"
	client = NotionAPIClient(token, page_size=15)
	
	assert client.notion_token == token
	assert client.page_size == 15
	assert client.headers["Authorization"] == f"Bearer {token}"
	# Check that Notion-Version follows YYYY-MM-DD format
	assert re.match(r"^\d{4}-\d{2}-\d{2}$", client.headers["Notion-Version"])


@pytest.mark.asyncio
async def test_get_page_raw_success():
	"""Test successful page retrieval."""
	token = "test_token"
	client = NotionAPIClient(token)
	
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
async def test_get_page_raw_error():
	"""Test page retrieval with HTTP error."""
	token = "test_token"
	client = NotionAPIClient(token)
	
	mock_response = AsyncMock()
	mock_response.status_code = 404
	mock_response.json = lambda: {"message": "Page not found"}
	
	with patch('operations.notionAPIClient.AsyncClientManager.wait_for_next_request'), \
		 patch('operations.notionAPIClient.AsyncClientManager.get_client') as mock_get_client:
		
		mock_client = AsyncMock()
		mock_client.get.return_value = mock_response
		mock_get_client.return_value = mock_client
		
		with pytest.raises(Exception) as exc_info:
			await client.get_page_raw("invalid-page-id")
		
		assert "HTTP 404" in str(exc_info.value)


@pytest.mark.asyncio
async def test_get_block_children_raw_with_cursor():
	"""Test block children retrieval with pagination cursor."""
	token = "test_token"
	client = NotionAPIClient(token)
	
	mock_response = AsyncMock()
	mock_response.status_code = 200
	mock_response.json = lambda: {"results": [], "has_more": False}
	
	with patch('operations.notionAPIClient.AsyncClientManager.wait_for_next_request'), \
		 patch('operations.notionAPIClient.AsyncClientManager.get_client') as mock_get_client:
		
		mock_client = AsyncMock()
		mock_client.get.return_value = mock_response
		mock_get_client.return_value = mock_client
		
		result = await client.get_block_children_raw("block-id", start_cursor="cursor-123", page_size=50)
		
		assert result == {"results": [], "has_more": False}
		mock_client.get.assert_called_once_with(
			"https://api.notion.com/v1/blocks/block-id/children?page_size=50&start_cursor=cursor-123",
			headers=client.headers,
			timeout=30.0
		)


@pytest.mark.asyncio
async def test_search_raw():
	"""Test search functionality."""
	token = "test_token"
	client = NotionAPIClient(token)
	
	mock_response = AsyncMock()
	mock_response.status_code = 200
	mock_response.json = lambda: {"results": [{"id": "result-1"}]}
	
	with patch('operations.notionAPIClient.AsyncClientManager.wait_for_next_request'), \
		 patch('operations.notionAPIClient.AsyncClientManager.get_client') as mock_get_client:
		
		mock_client = AsyncMock()
		mock_client.post.return_value = mock_response
		mock_get_client.return_value = mock_client
		
		result = await client.search_raw("test query", filter_type="page", start_cursor="cursor-456")
		
		assert result == {"results": [{"id": "result-1"}]}
		
		# Verify the payload structure
		call_args = mock_client.post.call_args
		payload = call_args[1]["json"]
		assert payload["query"] == "test query"
		assert payload["filter"]["value"] == "page"
		assert payload["start_cursor"] == "cursor-456"


@pytest.mark.asyncio
async def test_query_database_raw():
	"""Test database query functionality."""
	token = "test_token"
	client = NotionAPIClient(token)
	
	mock_response = AsyncMock()
	mock_response.status_code = 200
	mock_response.json = lambda: {"results": [{"id": "db-result-1"}]}
	
	filter_obj = {"property": "Status", "select": {"equals": "TODO"}}
	
	with patch('operations.notionAPIClient.AsyncClientManager.wait_for_next_request'), \
		 patch('operations.notionAPIClient.AsyncClientManager.get_client') as mock_get_client:
		
		mock_client = AsyncMock()
		mock_client.post.return_value = mock_response
		mock_get_client.return_value = mock_client
		
		result = await client.query_database_raw("db-id", filter_obj=filter_obj, start_cursor="db-cursor")
		
		assert result == {"results": [{"id": "db-result-1"}]}
		
		# Verify the payload structure
		call_args = mock_client.post.call_args
		payload = call_args[1]["json"]
		assert payload["filter"] == filter_obj
		assert payload["start_cursor"] == "db-cursor"


@pytest.mark.asyncio
async def test_context_manager():
	"""Test async context manager functionality."""
	token = "test_token"
	
	with patch('operations.notionAPIClient.AsyncClientManager.initialize') as mock_init:
		async with NotionAPIClient(token) as client:
			assert isinstance(client, NotionAPIClient)
			mock_init.assert_called_once()


# Integration test (only runs if NOTION_TOKEN is available)
@pytest.mark.asyncio
async def test_real_api_call(api_client):
	"""Test actual API call to Notion (requires valid token and page ID)."""
	page_id = os.getenv("NOTION_LANDING_PAGE_ID")
	if not page_id:
		pytest.skip("NOTION_LANDING_PAGE_ID not found in environment")
	
	async with api_client:
		try:
			result = await api_client.get_page_raw(page_id)
			assert "id" in result
			assert "object" in result
			assert result["object"] == "page"
		except Exception as e:
			pytest.fail(f"Real API call failed: {e}") 