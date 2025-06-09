import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any

from tz_common import CustomUUID

from ..operations.notionService import NotionService
from ..operations.notionAPIClient import NotionAPIClient
from ..operations.cacheOrchestrator import CacheOrchestrator
from ..operations.blockDict import BlockDict
from ..operations.blockCache import ObjectType
from ..operations.blockTree import BlockTree
from ..operations.exceptions import (
	InvalidUUIDError, BlockTreeRequiredError, CacheRetrievalError, 
	APIError, ObjectTypeVerificationError
)


# Test constants
TEST_UUID_PAGE = "123e4567e89b12d3a456426614174000"
TEST_UUID_DATABASE = "123e4567e89b12d3a456426614174001"
TEST_UUID_BLOCK = "123e4567e89b12d3a456426614174002"
TEST_UUID_CHILD1 = "123e4567e89b12d3a456426614174003"
TEST_UUID_CHILD2 = "123e4567e89b12d3a456426614174004"
TEST_UUID_CURSOR = "123e4567e89b12d3a456426614174005"
TEST_LANDING_PAGE_ID = "123e4567e89b12d3a456426614174006"

TEST_INT_ID_PAGE = 1
TEST_INT_ID_DATABASE = 2
TEST_INT_ID_BLOCK = 3
TEST_INT_ID_CHILD1 = 4
TEST_INT_ID_CHILD2 = 5

TEST_QUERY = "test query"
TEST_FILTER_TYPE = "page"
TEST_SORT = "descending"

TEST_PAGE_DATA = {
	"object": "page",
	"id": TEST_UUID_PAGE,
	"last_edited_time": "2023-01-01T00:00:00.000Z",
	"properties": {"title": {"title": [{"text": {"content": "Test Page"}}]}}
}

TEST_DATABASE_DATA = {
	"object": "database", 
	"id": TEST_UUID_DATABASE,
	"last_edited_time": "2023-01-01T00:00:00.000Z",
	"title": [{"text": {"content": "Test Database"}}]
}

TEST_BLOCK_DATA = {
	"object": "block",
	"id": TEST_UUID_BLOCK,
	"type": "paragraph",
	"paragraph": {"rich_text": [{"text": {"content": "Test block"}}]}
}

TEST_SEARCH_RESULTS = {
	"object": "list",
	"results": [TEST_PAGE_DATA],
	"has_more": False
}

TEST_DATABASE_QUERY_RESULTS = {
	"object": "list",
	"results": [TEST_PAGE_DATA],
	"has_more": False
}


class TestNotionService:
	"""Test suite for NotionService class."""

	@pytest.fixture
	def mock_api_client(self):
		"""Create mock API client."""
		return AsyncMock(spec=NotionAPIClient)

	@pytest.fixture
	def mock_cache_orchestrator(self):
		"""Create mock cache orchestrator."""
		return MagicMock(spec=CacheOrchestrator)

	@pytest.fixture
	def mock_index(self):
		"""Create mock index."""
		mock = MagicMock()
		def resolve_to_uuid_side_effect(x):
			if isinstance(x, str):
				try:
					return CustomUUID.from_string(x)
				except ValueError:
					return None  # Return None for invalid UUIDs
			return x
		
		def to_int_side_effect(uuid_input):
			# Handle single UUID case - return single integer
			if isinstance(uuid_input, CustomUUID):
				if str(uuid_input) == TEST_UUID_DATABASE:
					return TEST_INT_ID_DATABASE
				elif str(uuid_input) == TEST_UUID_PAGE:
					return TEST_INT_ID_PAGE
				elif str(uuid_input) == TEST_UUID_BLOCK:
					return TEST_INT_ID_BLOCK
				elif str(uuid_input) == TEST_UUID_CHILD1:
					return TEST_INT_ID_CHILD1
				elif str(uuid_input) == TEST_UUID_CHILD2:
					return TEST_INT_ID_CHILD2
				else:
					return None
			# Handle list case - return dictionary
			elif isinstance(uuid_input, list):
				result = {}
				for uuid_obj in uuid_input:
					if str(uuid_obj) == TEST_UUID_CHILD1:
						result[uuid_obj] = TEST_INT_ID_CHILD1
					elif str(uuid_obj) == TEST_UUID_CHILD2:
						result[uuid_obj] = TEST_INT_ID_CHILD2
					else:
						result[uuid_obj] = None
				return result
			else:
				return None
		
		mock.resolve_to_uuid.side_effect = resolve_to_uuid_side_effect
		mock.resolve_to_int.return_value = TEST_INT_ID_PAGE
		mock.to_int.side_effect = to_int_side_effect
		mock.get_uuid.side_effect = lambda x: CustomUUID.from_string(TEST_UUID_CHILD1) if x == TEST_INT_ID_CHILD1 else CustomUUID.from_string(TEST_UUID_CHILD2)
		return mock

	@pytest.fixture
	def mock_dependencies(self):
		"""Create all mock dependencies."""
		return {
			'url_index': MagicMock(),
			'block_holder': MagicMock(),
			'block_manager': MagicMock()
		}

	@pytest.fixture
	def notion_service(self, mock_api_client, mock_cache_orchestrator, mock_index, mock_dependencies):
		"""Create NotionService instance with mocked dependencies."""
		return NotionService(
			api_client=mock_api_client,
			cache_orchestrator=mock_cache_orchestrator,
			index=mock_index,
			url_index=mock_dependencies['url_index'],
			block_holder=mock_dependencies['block_holder'],
			block_manager=mock_dependencies['block_manager'],
			landing_page_id=CustomUUID.from_string(TEST_LANDING_PAGE_ID)
		)

	@pytest.mark.asyncio
	async def test_get_notion_page_details_with_page_id_cache_hit(self, notion_service, mock_cache_orchestrator):
		"""Test getting page details when page is in cache."""
		# Setup
		expected_result = BlockDict()
		expected_result.add_block(TEST_INT_ID_PAGE, TEST_PAGE_DATA)
		mock_cache_orchestrator.get_or_fetch_page.return_value = expected_result

		# Execute
		result = await notion_service.get_notion_page_details(page_id=TEST_UUID_PAGE)

		# Verify
		assert result == expected_result
		mock_cache_orchestrator.get_or_fetch_page.assert_called_once()

	@pytest.mark.asyncio
	async def test_get_notion_page_details_with_database_id_cache_hit(self, notion_service, mock_cache_orchestrator):
		"""Test getting database details when database is in cache."""
		# Setup
		expected_result = BlockDict()
		expected_result.add_block(TEST_INT_ID_DATABASE, TEST_DATABASE_DATA)
		mock_cache_orchestrator.get_or_fetch_database.return_value = expected_result

		# Execute
		result = await notion_service.get_notion_page_details(database_id=TEST_UUID_DATABASE)

		# Verify
		assert result == expected_result
		mock_cache_orchestrator.get_or_fetch_database.assert_called_once()

	@pytest.mark.asyncio
	async def test_get_notion_page_details_with_landing_page(self, notion_service, mock_cache_orchestrator):
		"""Test getting page details when no ID provided (uses landing page)."""
		# Setup
		expected_result = BlockDict()
		expected_result.add_block(TEST_INT_ID_PAGE, TEST_PAGE_DATA)
		mock_cache_orchestrator.get_or_fetch_page.return_value = expected_result

		# Execute
		result = await notion_service.get_notion_page_details()

		# Verify
		assert result == expected_result
		mock_cache_orchestrator.get_or_fetch_page.assert_called_once()

	@pytest.mark.asyncio
	async def test_get_notion_page_details_cache_miss_returns_none(self, notion_service, mock_cache_orchestrator):
		"""Test getting page details when cache returns None."""
		# Setup
		mock_cache_orchestrator.get_or_fetch_page.return_value = None

		# Execute & Verify
		with pytest.raises(CacheRetrievalError) as exc_info:
			await notion_service.get_notion_page_details(page_id=TEST_UUID_PAGE)
		
		assert exc_info.value.resource_type == "page"
		assert exc_info.value.resource_id == TEST_UUID_PAGE

	@pytest.mark.asyncio
	async def test_get_notion_page_details_exception_handling(self, notion_service, mock_cache_orchestrator):
		"""Test exception handling in get_notion_page_details."""
		# Setup
		mock_cache_orchestrator.get_or_fetch_page.side_effect = Exception("Test error")

		# Execute & Verify
		with pytest.raises(APIError) as exc_info:
			await notion_service.get_notion_page_details(page_id=TEST_UUID_PAGE)
		
		assert exc_info.value.operation == "get_notion_page_details"
		assert exc_info.value.original_error is not None

	@pytest.mark.asyncio
	async def test_get_block_children_success(self, notion_service, mock_cache_orchestrator, mock_index):
		"""Test successful retrieval of block children."""
		# Setup
		block_tree = MagicMock(spec=BlockTree)
		children_uuids = [CustomUUID.from_string(TEST_UUID_CHILD1), CustomUUID.from_string(TEST_UUID_CHILD2)]
		mock_cache_orchestrator.get_children_uuids.return_value = children_uuids

		# Mock the index methods
		mock_index.to_int.return_value = {
			CustomUUID.from_string(TEST_UUID_CHILD1): TEST_INT_ID_CHILD1,
			CustomUUID.from_string(TEST_UUID_CHILD2): TEST_INT_ID_CHILD2
		}
		mock_index.get_uuid.side_effect = lambda x: CustomUUID.from_string(TEST_UUID_CHILD1) if x == TEST_INT_ID_CHILD1 else CustomUUID.from_string(TEST_UUID_CHILD2)

		# Mock get_cached_block_content to return content for each child
		def mock_get_cached_block_content(uuid):
			if str(uuid) == TEST_UUID_CHILD1:
				return {"content": "child1"}
			elif str(uuid) == TEST_UUID_CHILD2:
				return {"content": "child2"}
			return None

		mock_cache_orchestrator.get_cached_block_content.side_effect = mock_get_cached_block_content

		# Execute
		result = await notion_service.get_block_children(TEST_UUID_BLOCK, block_tree)

		# Verify
		assert isinstance(result, BlockDict)
		result_dict = result.to_dict()
		assert TEST_INT_ID_CHILD1 in result_dict
		assert TEST_INT_ID_CHILD2 in result_dict
		assert result_dict[TEST_INT_ID_CHILD1] == {"content": "child1"}
		assert result_dict[TEST_INT_ID_CHILD2] == {"content": "child2"}
		block_tree.add_relationships.assert_called_once()

	@pytest.mark.asyncio
	async def test_get_block_children_invalid_uuid(self, notion_service, mock_index):
		"""Test get_block_children with invalid UUID."""
		# Setup
		mock_index.resolve_to_uuid.return_value = None
		block_tree = MagicMock(spec=BlockTree)

		# Execute & Verify
		with pytest.raises(InvalidUUIDError) as exc_info:
			await notion_service.get_block_children("invalid-uuid", block_tree)
		
		assert exc_info.value.uuid_value == "invalid-uuid"

	@pytest.mark.asyncio
	async def test_get_block_children_no_block_tree(self, notion_service):
		"""Test get_block_children without block_tree."""
		# Execute & Verify
		with pytest.raises(BlockTreeRequiredError) as exc_info:
			await notion_service.get_block_children(TEST_UUID_BLOCK, None)
		
		assert exc_info.value.operation == "get_block_children"

	@pytest.mark.asyncio
	async def test_get_block_content_success(self, notion_service, mock_cache_orchestrator, mock_index):
		"""Test successful block content retrieval."""
		# Setup
		block_tree = MagicMock(spec=BlockTree)
		expected_result = BlockDict()
		expected_result.add_block(TEST_INT_ID_BLOCK, TEST_BLOCK_DATA)
		mock_cache_orchestrator.get_or_fetch_block.return_value = expected_result
		
		# Mock is_children_fetched_for_block to return False so it goes through normal flow
		mock_cache_orchestrator.is_children_fetched_for_block.return_value = False
		
		# Mock get_all_children_recursively to prevent infinite recursion
		children_result = BlockDict()
		children_result.add_block(TEST_INT_ID_CHILD1, {"content": "child1"})
		
		async def mock_get_all_children_recursively(block_id, tree, visited_nodes=None):
			return children_result
		
		notion_service.get_all_children_recursively = mock_get_all_children_recursively

		# Execute
		result = await notion_service.get_block_content(TEST_UUID_BLOCK, block_tree=block_tree)

		# Verify - result should include both the main block and children
		assert isinstance(result, BlockDict)
		result_dict = result.to_dict()
		assert TEST_INT_ID_BLOCK in result_dict
		assert TEST_INT_ID_CHILD1 in result_dict
		block_tree.add_parent.assert_called_once()

	@pytest.mark.asyncio
	async def test_get_block_content_with_children_already_fetched(self, notion_service, mock_cache_orchestrator):
		"""Test get_block_content with children when already fetched."""
		# Setup
		block_tree = MagicMock(spec=BlockTree)
		mock_cache_orchestrator.is_children_fetched_for_block.return_value = True
		
		# Mock get_all_children_recursively
		expected_result = BlockDict()
		expected_result.add_block(TEST_INT_ID_CHILD1, {"content": "child1"})
		
		async def mock_get_all_children_recursively(block_id, tree, visited_nodes=None):
			return expected_result
		
		notion_service.get_all_children_recursively = mock_get_all_children_recursively

		# Execute
		result = await notion_service.get_block_content(TEST_UUID_BLOCK, block_tree=block_tree)

		# Verify
		assert result == expected_result

	@pytest.mark.asyncio
	async def test_get_block_content_no_block_tree(self, notion_service):
		"""Test get_block_content without block_tree."""
		# Execute & Verify
		with pytest.raises(BlockTreeRequiredError) as exc_info:
			await notion_service.get_block_content(TEST_UUID_BLOCK, block_tree=None)
		
		assert exc_info.value.operation == "get_block_content"

	@pytest.mark.asyncio
	async def test_get_block_content_invalid_block_id(self, notion_service, mock_index):
		"""Test get_block_content with invalid block ID."""
		# Setup
		block_tree = MagicMock(spec=BlockTree)
		mock_index.resolve_to_uuid.return_value = None

		# Execute & Verify
		with pytest.raises(InvalidUUIDError) as exc_info:
			await notion_service.get_block_content("invalid-id", block_tree=block_tree)
		
		assert exc_info.value.uuid_value == "invalid-id"

	@pytest.mark.asyncio
	async def test_get_block_content_cache_returns_none(self, notion_service, mock_cache_orchestrator):
		"""Test get_block_content when cache returns None."""
		# Setup
		block_tree = MagicMock(spec=BlockTree)
		mock_cache_orchestrator.get_or_fetch_block.return_value = None
		mock_cache_orchestrator.is_children_fetched_for_block.return_value = False

		# Execute & Verify
		with pytest.raises(CacheRetrievalError) as exc_info:
			await notion_service.get_block_content(TEST_UUID_BLOCK, block_tree=block_tree)
		
		assert exc_info.value.resource_type == "block"

	@pytest.mark.asyncio
	async def test_get_all_children_recursively_success(self, notion_service):
		"""Test successful recursive children retrieval."""
		# Setup
		block_tree = MagicMock(spec=BlockTree)
		
		# Mock get_block_children to return immediate children only for the parent
		# Return empty for children to avoid infinite recursion
		call_count = 0
		async def mock_get_block_children(uuid, tree):
			nonlocal call_count
			call_count += 1
			if call_count == 1:  # First call for parent
				immediate_children = BlockDict()
				immediate_children.add_block(TEST_INT_ID_CHILD1, {"content": "child1"})
				immediate_children.add_block(TEST_INT_ID_CHILD2, {"content": "child2"})
				return immediate_children
			else:  # Subsequent calls for children - return empty to stop recursion
				return BlockDict()
		
		notion_service.get_block_children = mock_get_block_children

		# Execute
		result = await notion_service.get_all_children_recursively(TEST_UUID_BLOCK, block_tree)

		# Verify
		assert isinstance(result, BlockDict)
		result_dict = result.to_dict()
		assert TEST_INT_ID_CHILD1 in result_dict
		assert TEST_INT_ID_CHILD2 in result_dict

	@pytest.mark.asyncio
	async def test_get_all_children_recursively_invalid_uuid(self, notion_service, mock_index):
		"""Test get_all_children_recursively with invalid UUID."""
		# Setup
		block_tree = MagicMock(spec=BlockTree)
		mock_index.resolve_to_uuid.return_value = None

		# Execute & Verify
		with pytest.raises(InvalidUUIDError) as exc_info:
			await notion_service.get_all_children_recursively("invalid-uuid", block_tree)
		
		assert exc_info.value.uuid_value == "invalid-uuid"

	@pytest.mark.asyncio
	async def test_search_notion_cache_hit(self, notion_service, mock_cache_orchestrator):
		"""Test search when results are in cache."""
		# Setup
		expected_result = BlockDict()
		expected_result.add_block(TEST_INT_ID_PAGE, TEST_PAGE_DATA)
		mock_cache_orchestrator.get_cached_search_results.return_value = expected_result

		# Execute
		result = await notion_service.search_notion(TEST_QUERY, TEST_FILTER_TYPE)

		# Verify
		assert result == expected_result
		mock_cache_orchestrator.get_cached_search_results.assert_called_once()

	@pytest.mark.asyncio
	async def test_search_notion_cache_miss(self, notion_service, mock_cache_orchestrator, mock_api_client):
		"""Test search when cache miss occurs."""
		# Setup
		mock_cache_orchestrator.get_cached_search_results.return_value = None
		mock_api_client.search_raw.return_value = TEST_SEARCH_RESULTS
		
		expected_result = BlockDict()
		expected_result.add_block(TEST_INT_ID_PAGE, TEST_PAGE_DATA)
		mock_cache_orchestrator.cache_search_results.return_value = expected_result

		# Execute
		result = await notion_service.search_notion(TEST_QUERY, TEST_FILTER_TYPE)

		# Verify
		assert result == expected_result
		mock_api_client.search_raw.assert_called_once()
		mock_cache_orchestrator.cache_search_results.assert_called_once()

	@pytest.mark.asyncio
	async def test_search_notion_with_cursor(self, notion_service, mock_cache_orchestrator, mock_index, mock_api_client):
		"""Test search with start cursor."""
		# Setup
		mock_cache_orchestrator.get_cached_search_results.return_value = None
		mock_api_client.search_raw.return_value = TEST_SEARCH_RESULTS
		expected_result = BlockDict()
		mock_cache_orchestrator.cache_search_results.return_value = expected_result

		# Execute
		result = await notion_service.search_notion(TEST_QUERY, start_cursor=TEST_UUID_CURSOR)

		# Verify
		assert result == expected_result
		mock_index.resolve_to_uuid.assert_called()

	@pytest.mark.asyncio
	async def test_search_notion_exception_handling(self, notion_service, mock_cache_orchestrator, mock_api_client):
		"""Test search exception handling."""
		# Setup
		mock_cache_orchestrator.get_cached_search_results.return_value = None
		mock_api_client.search_raw.side_effect = Exception("API error")

		# Execute & Verify
		with pytest.raises(APIError) as exc_info:
			await notion_service.search_notion(TEST_QUERY)
		
		assert exc_info.value.operation == "search_notion"

	@pytest.mark.asyncio
	async def test_query_database_cache_hit(self, notion_service, mock_cache_orchestrator):
		"""Test database query when results are in cache."""
		# Setup
		expected_result = BlockDict()
		expected_result.add_block(TEST_INT_ID_PAGE, TEST_PAGE_DATA)
		mock_cache_orchestrator.get_cached_database_query_results.return_value = expected_result

		# Execute
		result = await notion_service.query_database(TEST_UUID_DATABASE)

		# Verify
		assert result == expected_result
		mock_cache_orchestrator.get_cached_database_query_results.assert_called_once()

	@pytest.mark.asyncio
	async def test_query_database_cache_miss(self, notion_service, mock_cache_orchestrator, mock_api_client):
		"""Test database query when cache miss occurs."""
		# Setup
		mock_cache_orchestrator.get_cached_database_query_results.return_value = None
		mock_api_client.query_database_raw.return_value = TEST_DATABASE_QUERY_RESULTS
		
		expected_result = BlockDict()
		expected_result.add_block(TEST_INT_ID_PAGE, TEST_PAGE_DATA)
		mock_cache_orchestrator.cache_database_query_results.return_value = expected_result

		# Execute
		result = await notion_service.query_database(TEST_UUID_DATABASE)

		# Verify
		assert result == expected_result
		mock_api_client.query_database_raw.assert_called_once()
		mock_cache_orchestrator.cache_database_query_results.assert_called_once()

	@pytest.mark.asyncio
	async def test_query_database_with_filter(self, notion_service, mock_cache_orchestrator):
		"""Test database query with filter object."""
		# Setup
		filter_obj = {"property": "Status", "select": {"equals": "Done"}}
		expected_result = BlockDict()
		mock_cache_orchestrator.get_cached_database_query_results.return_value = expected_result

		# Execute
		result = await notion_service.query_database(TEST_UUID_DATABASE, filter_obj=filter_obj)

		# Verify
		assert result == expected_result

	@pytest.mark.asyncio
	async def test_query_database_object_type_verification_error(self, notion_service, mock_cache_orchestrator):
		"""Test database query with object type verification error."""
		# Setup
		mock_cache_orchestrator.verify_object_type_or_raise.side_effect = ValueError("Not a database")

		# Execute & Verify - should now get the original error message format with int_id
		with pytest.raises(ValueError) as exc_info:
			await notion_service.query_database(TEST_UUID_DATABASE)
		
		# Check that the error message contains the integer ID and the expected format
		error_message = str(exc_info.value)
		assert f"Database {TEST_INT_ID_DATABASE} was expected to be a database but it is a different type" == error_message

	@pytest.mark.asyncio
	async def test_query_database_exception_handling(self, notion_service, mock_cache_orchestrator, mock_api_client):
		"""Test database query exception handling."""
		# Setup
		mock_cache_orchestrator.get_cached_database_query_results.return_value = None
		mock_api_client.query_database_raw.side_effect = Exception("API error")

		# Execute & Verify
		with pytest.raises(APIError) as exc_info:
			await notion_service.query_database(TEST_UUID_DATABASE)
		
		assert exc_info.value.operation == "query_database" 