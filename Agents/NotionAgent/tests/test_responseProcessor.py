import pytest

from operations.utilities.responseProcessor import ResponseProcessor
from operations.blockDict import BlockDict


# Test Constants
TEST_PAGE_DATA = {"object": "page", "title": "Test Page"}
TEST_EMPTY_DATA = {}
TEST_COMPLEX_PAGE_DATA = {
	"object": "page",
	"properties": {
		"title": {"title": [{"text": {"content": "Complex Page"}}]},
		"status": {"select": {"name": "In Progress"}}
	}
}

TEST_SEARCH_RESULTS_BASIC = {
	"object": "list",
	"results": [
		{"id": 1, "object": "page", "title": "Page 1"},
		{"id": 2, "object": "page", "title": "Page 2"}
	],
	"has_more": False
}

TEST_SEARCH_RESULTS_STRING_IDS = {
	"object": "list",
	"results": [
		{"id": "abc-123", "object": "page", "title": "Page 1"},
		{"id": "def-456", "object": "page", "title": "Page 2"}
	],
	"has_more": False
}

TEST_SEARCH_RESULTS_NO_ID = {
	"object": "list",
	"results": [
		{"object": "page", "title": "Page 1"},
		{"object": "page", "title": "Page 2"}
	],
	"has_more": False
}

TEST_SEARCH_RESULTS_EMPTY = {
	"object": "list",
	"results": [],
	"has_more": False
}

TEST_DATABASE_QUERY_RESULTS = {
	"object": "list",
	"results": [
		{"id": 10, "object": "page", "properties": {"Name": {"title": [{"text": {"content": "Item 1"}}]}}},
		{"id": 20, "object": "page", "properties": {"Name": {"title": [{"text": {"content": "Item 2"}}]}}}
	],
	"has_more": False
}

TEST_RESPONSE_DATA_VALID = {
	"object": "list",
	"results": [
		{"id": 1, "title": "Item 1"},
		{"id": 2, "title": "Item 2"}
	]
}

TEST_RESPONSE_DATA_THREE_ITEMS = {
	"results": [
		{"id": 1, "title": "Item 1"},
		{"id": 2, "title": "Item 2"},
		{"id": 3, "title": "Item 3"}
	]
}

# Test IDs
TEST_ID_123 = 123
TEST_ID_456 = 456
TEST_ID_789 = 789

# Test strings
TEST_CURSOR = "abc123"
TEST_INVALID_INPUT = "not a dict"


class TestResponseProcessor:
	"""Test suite for ResponseProcessor utility class."""

	def test_wrap_in_block_dict_basic(self):
		"""Test wrap_in_block_dict with basic data."""
		result = ResponseProcessor.wrap_in_block_dict(TEST_PAGE_DATA, TEST_ID_123)
		
		assert isinstance(result, BlockDict)
		assert TEST_ID_123 in result.blocks
		assert result.blocks[TEST_ID_123] == TEST_PAGE_DATA

	def test_wrap_in_block_dict_empty_data(self):
		"""Test wrap_in_block_dict with empty data."""
		result = ResponseProcessor.wrap_in_block_dict(TEST_EMPTY_DATA, TEST_ID_456)
		
		assert isinstance(result, BlockDict)
		assert TEST_ID_456 in result.blocks
		assert result.blocks[TEST_ID_456] == TEST_EMPTY_DATA

	def test_wrap_in_block_dict_complex_data(self):
		"""Test wrap_in_block_dict with complex nested data."""
		result = ResponseProcessor.wrap_in_block_dict(TEST_COMPLEX_PAGE_DATA, TEST_ID_789)
		
		assert isinstance(result, BlockDict)
		assert TEST_ID_789 in result.blocks
		assert result.blocks[TEST_ID_789] == TEST_COMPLEX_PAGE_DATA

	def test_process_search_results_to_block_dict_basic(self):
		"""Test process_search_results_to_block_dict with basic search results."""
		result = ResponseProcessor.process_search_results_to_block_dict(TEST_SEARCH_RESULTS_BASIC)
		
		assert isinstance(result, BlockDict)
		assert len(result.blocks) == 2
		assert 1 in result.blocks
		assert 2 in result.blocks
		assert result.blocks[1]["title"] == "Page 1"
		assert result.blocks[2]["title"] == "Page 2"

	def test_process_search_results_to_block_dict_string_ids(self):
		"""Test process_search_results_to_block_dict with string IDs (uses index)."""
		result = ResponseProcessor.process_search_results_to_block_dict(TEST_SEARCH_RESULTS_STRING_IDS)
		
		assert isinstance(result, BlockDict)
		assert len(result.blocks) == 2
		assert 0 in result.blocks  # Uses index since ID is string
		assert 1 in result.blocks
		assert result.blocks[0]["title"] == "Page 1"
		assert result.blocks[1]["title"] == "Page 2"

	def test_process_search_results_to_block_dict_no_id(self):
		"""Test process_search_results_to_block_dict when results have no ID."""
		result = ResponseProcessor.process_search_results_to_block_dict(TEST_SEARCH_RESULTS_NO_ID)
		
		assert isinstance(result, BlockDict)
		assert len(result.blocks) == 2
		assert 0 in result.blocks
		assert 1 in result.blocks

	def test_process_search_results_to_block_dict_empty_results(self):
		"""Test process_search_results_to_block_dict with empty results."""
		result = ResponseProcessor.process_search_results_to_block_dict(TEST_SEARCH_RESULTS_EMPTY)
		
		assert isinstance(result, BlockDict)
		assert len(result.blocks) == 0

	def test_process_search_results_to_block_dict_no_results_key(self):
		"""Test process_search_results_to_block_dict when no results key."""
		no_results_data = {"object": "list", "has_more": False}
		result = ResponseProcessor.process_search_results_to_block_dict(no_results_data)
		
		assert isinstance(result, BlockDict)
		assert len(result.blocks) == 0

	def test_process_search_results_to_block_dict_invalid_input(self):
		"""Test process_search_results_to_block_dict with invalid input."""
		result = ResponseProcessor.process_search_results_to_block_dict(TEST_INVALID_INPUT)
		
		assert isinstance(result, BlockDict)
		assert len(result.blocks) == 0

	def test_process_database_query_results_to_block_dict_basic(self):
		"""Test process_database_query_results_to_block_dict with basic results."""
		result = ResponseProcessor.process_database_query_results_to_block_dict(TEST_DATABASE_QUERY_RESULTS)
		
		assert isinstance(result, BlockDict)
		assert len(result.blocks) == 2
		assert 10 in result.blocks
		assert 20 in result.blocks

	def test_extract_results_list_valid(self):
		"""Test extract_results_list with valid response data."""
		result = ResponseProcessor.extract_results_list(TEST_RESPONSE_DATA_VALID)
		
		assert len(result) == 2
		assert result[0]["title"] == "Item 1"
		assert result[1]["title"] == "Item 2"

	def test_extract_results_list_empty(self):
		"""Test extract_results_list with empty results."""
		empty_response = {"object": "list", "results": []}
		result = ResponseProcessor.extract_results_list(empty_response)
		
		assert result == []

	def test_extract_results_list_no_results_key(self):
		"""Test extract_results_list when no results key."""
		no_results_response = {"object": "list", "has_more": False}
		result = ResponseProcessor.extract_results_list(no_results_response)
		
		assert result == []

	def test_extract_results_list_invalid_input(self):
		"""Test extract_results_list with invalid input."""
		result = ResponseProcessor.extract_results_list(TEST_INVALID_INPUT)
		
		assert result == []

	def test_extract_results_list_results_not_list(self):
		"""Test extract_results_list when results is not a list."""
		invalid_results_response = {"object": "list", "results": "not a list"}
		result = ResponseProcessor.extract_results_list(invalid_results_response)
		
		assert result == []

	def test_has_more_results_true(self):
		"""Test has_more_results returns True when has_more is True."""
		response_data = {"has_more": True}
		result = ResponseProcessor.has_more_results(response_data)
		assert result is True

	def test_has_more_results_false(self):
		"""Test has_more_results returns False when has_more is False."""
		response_data = {"has_more": False}
		result = ResponseProcessor.has_more_results(response_data)
		assert result is False

	def test_has_more_results_missing(self):
		"""Test has_more_results returns False when has_more is missing."""
		response_data = {}
		result = ResponseProcessor.has_more_results(response_data)
		assert result is False

	def test_get_next_cursor_present(self):
		"""Test get_next_cursor returns cursor when present."""
		cursor_response = {"next_cursor": TEST_CURSOR}
		result = ResponseProcessor.get_next_cursor(cursor_response)
		assert result == TEST_CURSOR

	def test_get_next_cursor_missing(self):
		"""Test get_next_cursor returns None when missing."""
		empty_response = {}
		result = ResponseProcessor.get_next_cursor(empty_response)
		assert result is None

	def test_get_next_cursor_null(self):
		"""Test get_next_cursor returns None when null."""
		null_cursor_response = {"next_cursor": None}
		result = ResponseProcessor.get_next_cursor(null_cursor_response)
		assert result is None

	def test_count_results_basic(self):
		"""Test count_results with basic response."""
		result = ResponseProcessor.count_results(TEST_RESPONSE_DATA_THREE_ITEMS)
		assert result == 3

	def test_count_results_empty(self):
		"""Test count_results with empty results."""
		empty_results_response = {"results": []}
		result = ResponseProcessor.count_results(empty_results_response)
		assert result == 0

	def test_count_results_no_results(self):
		"""Test count_results when no results key."""
		no_results_response = {}
		result = ResponseProcessor.count_results(no_results_response)
		assert result == 0 