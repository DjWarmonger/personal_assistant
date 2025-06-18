import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from tz_common import CustomUUID
from operations.blocks.cacheOrchestrator import CacheOrchestrator
from operations.blocks.blockCache import BlockCache, ObjectType
from operations.blocks.blockManager import BlockManager
from operations.blocks.blockDict import BlockDict
from operations.blocks.index import Index
from operations.urlIndex import UrlIndex
from operations.blocks.blockHolder import BlockHolder


@pytest.fixture
def mock_cache():
	"""Create a mock BlockCache for testing."""
	return MagicMock(spec=BlockCache)


@pytest.fixture
def mock_block_manager():
	"""Create a mock BlockManager for testing."""
	mock = MagicMock(spec=BlockManager)
	# Add caption_processor attribute to avoid AttributeError in _queue_caption_for_cached_block
	mock.caption_processor = None  # Default to None (no caption processor)
	return mock


@pytest.fixture
def mock_index():
	"""Create a mock Index for testing."""
	mock = MagicMock(spec=Index)
	# Set up default return value for to_int method
	mock.to_int.return_value = 123  # Default integer ID for tests
	return mock


@pytest.fixture
def cache_orchestrator(mock_cache, mock_block_manager, mock_index):
	"""Create a CacheOrchestrator instance for testing."""
	return CacheOrchestrator(mock_cache, mock_block_manager, mock_index)


@pytest.fixture
def sample_uuid():
	"""Create a sample CustomUUID for testing."""
	return TestCacheOrchestrator.TEST_UUID_MAIN


@pytest.fixture
def sample_page_data():
	"""Create sample page data for testing."""
	return {
		"id": str(TestCacheOrchestrator.TEST_UUID_MAIN),
		"object": "page",
		"last_edited_time": TestCacheOrchestrator.TEST_TIMESTAMP,
		"properties": {
			"title": {
				"title": [{"text": {"content": "Test Page"}}]
			}
		}
	}


@pytest.fixture
def sample_database_data():
	"""Create sample database data for testing."""
	return {
		"id": str(TestCacheOrchestrator.TEST_UUID_MAIN),
		"object": "database",
		"last_edited_time": TestCacheOrchestrator.TEST_TIMESTAMP,
		"title": [{"text": {"content": "Test Database"}}]
	}


@pytest.fixture
def sample_block_data():
	"""Create sample block children data for testing."""
	return {
		"object": "list",
		"results": [
			{
				"id": str(TestCacheOrchestrator.TEST_UUID_CHILD1),
				"object": "block",
				"last_edited_time": TestCacheOrchestrator.TEST_TIMESTAMP,
				"type": "paragraph"
			}
		],
		"has_more": False
	}


class TestCacheOrchestrator:
	"""Test suite for CacheOrchestrator class."""

	# Test data constants
	TEST_UUID_MAIN = CustomUUID.from_string("123e4567-e89b-12d3-a456-426614174000")
	TEST_UUID_CHILD1 = CustomUUID.from_string("456e7890-e89b-12d3-a456-426614174001")
	TEST_UUID_SEARCH_RESULT = CustomUUID.from_string("789e1234-e89b-12d3-a456-426614174002")
	TEST_UUID_DB_PAGE = CustomUUID.from_string("abc12345-e89b-12d3-a456-426614174003")
	TEST_UUID_CHILD2 = CustomUUID.from_string("def56789-e89b-12d3-a456-426614174004")
	TEST_UUID_CHILD3 = CustomUUID.from_string("fed98765-e89b-12d3-a456-426614174005")

	TEST_TIMESTAMP = "2023-01-01T12:00:00.000Z"
	TEST_QUERY = "test query"
	TEST_FILTER_PAGE = "page"
	TEST_FILTER_STATUS = '{"property": "Status"}'
	TEST_FILTER_STATUS_DONE = '{"property": "Status", "select": {"equals": "Done"}}'
	TEST_CACHE_KEY = "test-cache-key"
	TEST_TTL = 3600

	@pytest.mark.asyncio
	async def test_get_or_fetch_page_cache_hit(self, cache_orchestrator, mock_cache, mock_block_manager, mock_index, sample_uuid):
		"""Test get_or_fetch_page when data is in cache."""
		# Setup
		cached_content = '{"object": "page", "title": "Cached Page"}'
		parsed_data = {"object": "page", "title": "Cached Page"}
		expected_int_id = 456
		
		mock_cache.get_page.return_value = cached_content
		mock_block_manager.parse_cache_content.return_value = parsed_data
		mock_index.to_int.return_value = expected_int_id
		
		# Mock fetcher function (should not be called)
		fetcher_func = AsyncMock()
		
		# Execute
		result = await cache_orchestrator.get_or_fetch_page(sample_uuid, fetcher_func)
		
		# Verify
		assert isinstance(result, BlockDict)
		assert expected_int_id in result.blocks  # Verify proper integer ID is used
		assert result.blocks[expected_int_id] == parsed_data
		mock_cache.get_page.assert_called_once_with(sample_uuid)
		mock_block_manager.parse_cache_content.assert_called_once_with(cached_content)
		mock_index.to_int.assert_called_once_with(sample_uuid)
		fetcher_func.assert_not_called()


	@pytest.mark.asyncio
	async def test_get_or_fetch_page_cache_miss(self, cache_orchestrator, mock_cache, mock_block_manager, sample_uuid, sample_page_data):
		"""Test get_or_fetch_page when data is not in cache."""
		# Setup
		mock_cache.get_page.side_effect = [None, '{"object": "page", "title": "Fetched Page"}']  # First call returns None, second returns cached data
		mock_block_manager.parse_cache_content.return_value = {"object": "page", "title": "Fetched Page"}
		mock_block_manager.process_and_store_block.return_value = 123
		
		# Mock fetcher function
		fetcher_func = AsyncMock(return_value=sample_page_data)
		
		# Execute
		result = await cache_orchestrator.get_or_fetch_page(sample_uuid, fetcher_func)
		
		# Verify
		assert isinstance(result, BlockDict)
		fetcher_func.assert_called_once()
		mock_block_manager.process_and_store_block.assert_called_once_with(sample_page_data, ObjectType.PAGE)


	@pytest.mark.asyncio
	async def test_get_or_fetch_database_cache_hit(self, cache_orchestrator, mock_cache, mock_block_manager, mock_index, sample_uuid):
		"""Test get_or_fetch_database when data is in cache."""
		# Setup
		cached_content = '{"object": "database", "title": "Cached Database"}'
		parsed_data = {"object": "database", "title": "Cached Database"}
		expected_int_id = 789
		
		mock_cache.get_database.return_value = cached_content
		mock_block_manager.parse_cache_content.return_value = parsed_data
		mock_index.to_int.return_value = expected_int_id
		
		# Mock fetcher function (should not be called)
		fetcher_func = AsyncMock()
		
		# Execute
		result = await cache_orchestrator.get_or_fetch_database(sample_uuid, fetcher_func)
		
		# Verify
		assert isinstance(result, BlockDict)
		assert expected_int_id in result.blocks  # Verify proper integer ID is used
		assert result.blocks[expected_int_id] == parsed_data
		mock_cache.get_database.assert_called_once_with(sample_uuid)
		mock_block_manager.parse_cache_content.assert_called_once_with(cached_content)
		mock_index.to_int.assert_called_once_with(sample_uuid)
		fetcher_func.assert_not_called()


	@pytest.mark.asyncio
	async def test_get_or_fetch_block_cache_miss(self, cache_orchestrator, mock_cache, mock_block_manager, sample_uuid, sample_block_data):
		"""Test get_or_fetch_block when data is not in cache."""
		# Setup
		mock_cache.get_block.return_value = None
		mock_block_manager.process_children_response.return_value = BlockDict()
		
		# Mock fetcher function
		fetcher_func = AsyncMock(return_value=sample_block_data)
		
		# Execute
		result = await cache_orchestrator.get_or_fetch_block(sample_uuid, fetcher_func)
		
		# Verify
		assert isinstance(result, BlockDict)
		fetcher_func.assert_called_once()
		mock_block_manager.process_children_response.assert_called_once_with(
			sample_block_data, sample_uuid, ObjectType.BLOCK
		)


	def test_get_cached_search_results_hit(self, cache_orchestrator, mock_cache, mock_block_manager):
		"""Test get_cached_search_results when results are cached."""
		# Setup
		start_cursor = self.TEST_UUID_MAIN
		
		cached_content = '{"results": [{"id": "result1", "object": "page"}]}'
		parsed_data = {"results": [{"id": "result1", "object": "page"}]}
		
		mock_cache.get_search_results.return_value = cached_content
		mock_block_manager.parse_cache_content.return_value = parsed_data
		
		# Execute
		result = cache_orchestrator.get_cached_search_results(self.TEST_QUERY, self.TEST_FILTER_PAGE, start_cursor)
		
		# Verify
		assert isinstance(result, BlockDict)
		mock_cache.get_search_results.assert_called_once_with(self.TEST_QUERY, self.TEST_FILTER_PAGE, start_cursor)
		mock_block_manager.parse_cache_content.assert_called_once_with(cached_content)


	def test_get_cached_search_results_miss(self, cache_orchestrator, mock_cache):
		"""Test get_cached_search_results when results are not cached."""
		# Setup
		mock_cache.get_search_results.return_value = None
		
		# Execute
		result = cache_orchestrator.get_cached_search_results(self.TEST_QUERY)
		
		# Verify
		assert result is None
		mock_cache.get_search_results.assert_called_once_with(self.TEST_QUERY, None, None)


	@pytest.mark.asyncio
	async def test_cache_search_results(self, cache_orchestrator, mock_cache, mock_block_manager):
		"""Test cache_search_results functionality."""
		# Setup
		results = {
			"results": [
				{
					"id": str(self.TEST_UUID_SEARCH_RESULT),
					"object": "page",
					"last_edited_time": self.TEST_TIMESTAMP
				}
			]
		}
		start_cursor = self.TEST_UUID_MAIN
		
		expected_block_dict = BlockDict()
		mock_block_manager.process_and_store_search_results.return_value = expected_block_dict
		
		# Execute
		result = await cache_orchestrator.cache_search_results(self.TEST_QUERY, results, self.TEST_FILTER_PAGE, start_cursor, self.TEST_TTL)
		
		# Verify
		assert result == expected_block_dict
		mock_cache.invalidate_page_if_expired.assert_called_once()
		mock_block_manager.process_and_store_search_results.assert_called_once_with(
			self.TEST_QUERY, results, self.TEST_FILTER_PAGE, start_cursor, self.TEST_TTL
		)


	def test_get_cached_database_query_results_hit(self, cache_orchestrator, mock_cache, mock_block_manager, sample_uuid):
		"""Test get_cached_database_query_results when results are cached."""
		# Setup
		start_cursor = self.TEST_UUID_MAIN
		
		cached_content = '{"results": [{"id": "page1", "object": "page"}]}'
		parsed_data = {"results": [{"id": "page1", "object": "page"}]}
		
		mock_cache.get_database_query_results.return_value = cached_content
		mock_block_manager.parse_cache_content.return_value = parsed_data
		
		# Execute
		result = cache_orchestrator.get_cached_database_query_results(sample_uuid, self.TEST_FILTER_STATUS_DONE, start_cursor)
		
		# Verify
		assert isinstance(result, BlockDict)
		mock_cache.get_database_query_results.assert_called_once_with(sample_uuid, self.TEST_FILTER_STATUS_DONE, start_cursor)
		mock_block_manager.parse_cache_content.assert_called_once_with(cached_content)


	@pytest.mark.asyncio
	async def test_cache_database_query_results(self, cache_orchestrator, mock_cache, mock_block_manager, sample_uuid):
		"""Test cache_database_query_results functionality."""
		# Setup
		results = {
			"results": [
				{
									"id": str(self.TEST_UUID_DB_PAGE),
				"object": "page",
				"last_edited_time": self.TEST_TIMESTAMP
				}
			]
		}
		start_cursor = self.TEST_UUID_MAIN
		
		expected_block_dict = BlockDict()
		mock_block_manager.process_and_store_database_query_results.return_value = expected_block_dict
		
		# Execute
		result = await cache_orchestrator.cache_database_query_results(sample_uuid, results, self.TEST_FILTER_STATUS, start_cursor)
		
		# Verify
		assert result == expected_block_dict
		mock_cache.invalidate_page_if_expired.assert_called_once()
		mock_block_manager.process_and_store_database_query_results.assert_called_once_with(
			sample_uuid, results, self.TEST_FILTER_STATUS, start_cursor
		)


	def test_invalidate_if_expired_database(self, cache_orchestrator, mock_cache, sample_uuid):
		"""Test invalidate_if_expired for database objects."""
		# Setup
		mock_cache.invalidate_database_if_expired.return_value = True
		
		# Execute
		result = cache_orchestrator.invalidate_if_expired(sample_uuid, self.TEST_TIMESTAMP, ObjectType.DATABASE)
		
		# Verify
		assert result is True
		mock_cache.invalidate_database_if_expired.assert_called_once_with(sample_uuid, self.TEST_TIMESTAMP)


	def test_invalidate_if_expired_page(self, cache_orchestrator, mock_cache, sample_uuid):
		"""Test invalidate_if_expired for page objects."""
		# Execute
		result = cache_orchestrator.invalidate_if_expired(sample_uuid, self.TEST_TIMESTAMP, ObjectType.PAGE)
		
		# Verify
		assert result is True  # Always returns True for pages
		mock_cache.invalidate_page_if_expired.assert_called_once_with(sample_uuid, self.TEST_TIMESTAMP)


	def test_invalidate_if_expired_block(self, cache_orchestrator, mock_cache, sample_uuid):
		"""Test invalidate_if_expired for block objects."""
		# Setup
		mock_cache.invalidate_block_if_expired.return_value = False
		
		# Execute
		result = cache_orchestrator.invalidate_if_expired(sample_uuid, self.TEST_TIMESTAMP, ObjectType.BLOCK)
		
		# Verify
		assert result is False
		mock_cache.invalidate_block_if_expired.assert_called_once_with(sample_uuid, self.TEST_TIMESTAMP)


	def test_verify_object_type_or_raise(self, cache_orchestrator, mock_cache, sample_uuid):
		"""Test verify_object_type_or_raise delegation."""
		# Execute
		cache_orchestrator.verify_object_type_or_raise(sample_uuid, ObjectType.DATABASE)
		
		# Verify
		mock_cache.verify_object_type_or_raise.assert_called_once_with(sample_uuid, ObjectType.DATABASE)


	def test_get_children_uuids(self, cache_orchestrator, mock_cache, sample_uuid):
		"""Test get_children_uuids delegation."""
		# Setup
		expected_children = [self.TEST_UUID_CHILD2, self.TEST_UUID_CHILD3]
		mock_cache.get_children_uuids.return_value = expected_children
		
		# Execute
		result = cache_orchestrator.get_children_uuids(sample_uuid)
		
		# Verify
		assert result == expected_children
		mock_cache.get_children_uuids.assert_called_once_with(sample_uuid)


	def test_is_children_fetched_for_block(self, cache_orchestrator, mock_cache):
		"""Test is_children_fetched_for_block delegation."""
		# Setup
		mock_cache.get_children_fetched_for_block.return_value = True
		
		# Execute
		result = cache_orchestrator.is_children_fetched_for_block(self.TEST_CACHE_KEY)
		
		# Verify
		assert result is True
		mock_cache.get_children_fetched_for_block.assert_called_once_with(self.TEST_CACHE_KEY)


	@pytest.mark.asyncio
	async def test_get_or_fetch_page_error_handling(self, cache_orchestrator, mock_cache, sample_uuid):
		"""Test error handling in get_or_fetch_page."""
		# Setup
		mock_cache.get_page.return_value = None
		fetcher_func = AsyncMock(side_effect=Exception("API Error"))
		
		# Execute
		result = await cache_orchestrator.get_or_fetch_page(sample_uuid, fetcher_func)
		
		# Verify
		assert result is None
		fetcher_func.assert_called_once()


	@pytest.mark.asyncio
	async def test_get_or_fetch_database_error_handling(self, cache_orchestrator, mock_cache, sample_uuid):
		"""Test error handling in get_or_fetch_database."""
		# Setup
		mock_cache.get_database.return_value = None
		fetcher_func = AsyncMock(side_effect=Exception("API Error"))
		
		# Execute
		result = await cache_orchestrator.get_or_fetch_database(sample_uuid, fetcher_func)
		
		# Verify
		assert result is None
		fetcher_func.assert_called_once()


	@pytest.mark.asyncio
	async def test_get_or_fetch_block_error_handling(self, cache_orchestrator, mock_cache, sample_uuid):
		"""Test error handling in get_or_fetch_block."""
		# Setup
		mock_cache.get_block.return_value = None
		fetcher_func = AsyncMock(side_effect=Exception("API Error"))
		
		# Execute
		result = await cache_orchestrator.get_or_fetch_block(sample_uuid, fetcher_func)
		
		# Verify
		assert result is None
		fetcher_func.assert_called_once()


	@pytest.mark.asyncio
	async def test_get_or_fetch_page_uuid_conversion_failure(self, cache_orchestrator, mock_cache, mock_block_manager, mock_index, sample_uuid):
		"""Test get_or_fetch_page when UUID to int conversion fails."""
		# Setup
		cached_content = '{"object": "page", "title": "Cached Page"}'
		parsed_data = {"object": "page", "title": "Cached Page"}
		
		mock_cache.get_page.return_value = cached_content
		mock_block_manager.parse_cache_content.return_value = parsed_data
		mock_index.to_int.return_value = None  # Simulate conversion failure
		
		# Mock fetcher function (should not be called)
		fetcher_func = AsyncMock()
		
		# Execute
		result = await cache_orchestrator.get_or_fetch_page(sample_uuid, fetcher_func)
		
		# Verify
		assert result is None
		mock_cache.get_page.assert_called_once_with(sample_uuid)
		mock_block_manager.parse_cache_content.assert_called_once_with(cached_content)
		mock_index.to_int.assert_called_once_with(sample_uuid)
		fetcher_func.assert_not_called()


	@pytest.mark.asyncio
	async def test_get_or_fetch_database_uuid_conversion_failure(self, cache_orchestrator, mock_cache, mock_block_manager, mock_index, sample_uuid):
		"""Test get_or_fetch_database when UUID to int conversion fails."""
		# Setup
		cached_content = '{"object": "database", "title": "Cached Database"}'
		parsed_data = {"object": "database", "title": "Cached Database"}
		
		mock_cache.get_database.return_value = cached_content
		mock_block_manager.parse_cache_content.return_value = parsed_data
		mock_index.to_int.return_value = None  # Simulate conversion failure
		
		# Mock fetcher function (should not be called)
		fetcher_func = AsyncMock()
		
		# Execute
		result = await cache_orchestrator.get_or_fetch_database(sample_uuid, fetcher_func)
		
		# Verify
		assert result is None
		mock_cache.get_database.assert_called_once_with(sample_uuid)
		mock_block_manager.parse_cache_content.assert_called_once_with(cached_content)
		mock_index.to_int.assert_called_once_with(sample_uuid)
		fetcher_func.assert_not_called()


	@pytest.mark.asyncio
	async def test_get_or_fetch_block_uuid_conversion_failure(self, cache_orchestrator, mock_cache, mock_block_manager, mock_index, sample_uuid):
		"""Test get_or_fetch_block when UUID to int conversion fails."""
		# Setup
		cached_content = '{"object": "block", "type": "paragraph"}'
		parsed_data = {"object": "block", "type": "paragraph"}
		
		mock_cache.get_block.return_value = cached_content
		mock_block_manager.parse_cache_content.return_value = parsed_data
		mock_index.to_int.return_value = None  # Simulate conversion failure
		
		# Mock fetcher function (should not be called)
		fetcher_func = AsyncMock()
		
		# Execute
		result = await cache_orchestrator.get_or_fetch_block(sample_uuid, fetcher_func)
		
		# Verify
		assert result is None
		mock_cache.get_block.assert_called_once_with(sample_uuid)
		mock_block_manager.parse_cache_content.assert_called_once_with(cached_content)
		mock_index.to_int.assert_called_once_with(sample_uuid)
		fetcher_func.assert_not_called()


class TestCacheOrchestratorCaptionIntegration:
	"""Test suite for CacheOrchestrator caption generation integration."""

	@pytest.mark.asyncio
	async def test_get_or_fetch_page_triggers_caption_generation(self, mock_cache, mock_index, sample_uuid, sample_page_data):
		"""Test that get_or_fetch_page triggers caption generation through BlockManager."""
		# Setup
		mock_cache.get_page.side_effect = [None, '{"object": "page", "title": "Fetched Page"}']
		mock_block_manager = MagicMock(spec=BlockManager)
		mock_block_manager.parse_cache_content.return_value = {"object": "page", "title": "Fetched Page"}
		mock_block_manager.process_and_store_block.return_value = 123
		
		cache_orchestrator = CacheOrchestrator(mock_cache, mock_block_manager, mock_index)
		
		# Mock fetcher function
		fetcher_func = AsyncMock(return_value=sample_page_data)
		
		# Execute
		result = await cache_orchestrator.get_or_fetch_page(sample_uuid, fetcher_func)
		
		# Verify that BlockManager.process_and_store_block was called
		# (which includes caption generation logic)
		assert isinstance(result, BlockDict)
		mock_block_manager.process_and_store_block.assert_called_once_with(sample_page_data, ObjectType.PAGE)

	@pytest.mark.asyncio
	async def test_get_or_fetch_database_triggers_caption_generation(self, mock_cache, mock_index, sample_uuid, sample_database_data):
		"""Test that get_or_fetch_database triggers caption generation through BlockManager."""
		# Setup
		mock_cache.get_database.side_effect = [None, '{"object": "database", "title": "Fetched Database"}']
		mock_block_manager = MagicMock(spec=BlockManager)
		mock_block_manager.parse_cache_content.return_value = {"object": "database", "title": "Fetched Database"}
		mock_block_manager.process_and_store_block.return_value = 456
		
		cache_orchestrator = CacheOrchestrator(mock_cache, mock_block_manager, mock_index)
		
		# Mock fetcher function
		fetcher_func = AsyncMock(return_value=sample_database_data)
		
		# Execute
		result = await cache_orchestrator.get_or_fetch_database(sample_uuid, fetcher_func)
		
		# Verify that BlockManager.process_and_store_block was called
		# (which includes caption generation logic)
		assert isinstance(result, BlockDict)
		mock_block_manager.process_and_store_block.assert_called_once_with(sample_database_data, ObjectType.DATABASE)

	@pytest.mark.asyncio
	async def test_cache_search_results_triggers_caption_generation(self, mock_cache, mock_index):
		"""Test that cache_search_results triggers caption generation through BlockManager."""
		# Setup
		search_results = {
			"results": [
				{
					"id": str(TestCacheOrchestrator.TEST_UUID_SEARCH_RESULT),
					"object": "page",
					"last_edited_time": TestCacheOrchestrator.TEST_TIMESTAMP,
					"title": "Search Result Page"
				}
			]
		}
		
		mock_block_manager = MagicMock(spec=BlockManager)
		expected_block_dict = BlockDict()
		mock_block_manager.process_and_store_search_results.return_value = expected_block_dict
		
		cache_orchestrator = CacheOrchestrator(mock_cache, mock_block_manager, mock_index)
		
		# Execute
		result = await cache_orchestrator.cache_search_results(TestCacheOrchestrator.TEST_QUERY, search_results)
		
		# Verify that BlockManager.process_and_store_search_results was called
		# (which includes caption generation logic for each search result)
		assert result == expected_block_dict
		mock_block_manager.process_and_store_search_results.assert_called_once_with(
			TestCacheOrchestrator.TEST_QUERY, search_results, None, None, None
		)

	@pytest.mark.asyncio
	async def test_cache_database_query_results_triggers_caption_generation(self, mock_cache, mock_index, sample_uuid):
		"""Test that cache_database_query_results triggers caption generation through BlockManager."""
		# Setup
		query_results = {
			"results": [
				{
					"id": str(TestCacheOrchestrator.TEST_UUID_DB_PAGE),
					"object": "page",
					"last_edited_time": TestCacheOrchestrator.TEST_TIMESTAMP,
					"properties": {"title": {"title": [{"text": {"content": "Database Page"}}]}}
				}
			]
		}
		
		mock_block_manager = MagicMock(spec=BlockManager)
		expected_block_dict = BlockDict()
		mock_block_manager.process_and_store_database_query_results.return_value = expected_block_dict
		
		cache_orchestrator = CacheOrchestrator(mock_cache, mock_block_manager, mock_index)
		
		# Execute
		result = await cache_orchestrator.cache_database_query_results(sample_uuid, query_results)
		
		# Verify that BlockManager.process_and_store_database_query_results was called
		# (which includes caption generation logic for each database page)
		assert result == expected_block_dict
		mock_block_manager.process_and_store_database_query_results.assert_called_once_with(
			sample_uuid, query_results, None, None
		)

	@pytest.mark.asyncio
	async def test_get_or_fetch_block_triggers_caption_generation_for_children(self, mock_cache, mock_index, sample_uuid, sample_block_data):
		"""Test that get_or_fetch_block triggers caption generation for children through BlockManager."""
		# Setup
		mock_cache.get_block.return_value = None
		mock_block_manager = MagicMock(spec=BlockManager)
		expected_block_dict = BlockDict()
		mock_block_manager.process_children_response.return_value = expected_block_dict
		
		cache_orchestrator = CacheOrchestrator(mock_cache, mock_block_manager, mock_index)
		
		# Mock fetcher function
		fetcher_func = AsyncMock(return_value=sample_block_data)
		
		# Execute
		result = await cache_orchestrator.get_or_fetch_block(sample_uuid, fetcher_func)
		
		# Verify that BlockManager.process_children_response was called
		# (which includes caption generation logic for each child block)
		assert result == expected_block_dict
		mock_block_manager.process_children_response.assert_called_once_with(
			sample_block_data, sample_uuid, ObjectType.BLOCK
		) 