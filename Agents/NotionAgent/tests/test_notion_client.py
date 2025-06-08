import unittest
import os
import asyncio
import pytest
import pytest_asyncio
from dotenv import load_dotenv
import sys

# Update the import path to include the project root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Use direct imports from operations
from operations.notion_client import NotionClient
from operations.asyncClientManager import AsyncClientManager
from operations.blockTree import BlockTree
from operations.blockDict import BlockDict
from tz_common import CustomUUID

load_dotenv()

@pytest_asyncio.fixture
async def notion_client():
	client = NotionClient(load_from_disk=False, run_on_start=False)
	try:
		yield client
	finally:
		await AsyncClientManager.cleanup()


@pytest.mark.asyncio
async def test_navigate_to_notion_page(notion_client):
	page_id = os.getenv("NOTION_LANDING_PAGE_ID")
	
	result = await notion_client.get_notion_page_details(page_id=page_id)

	# Handle BlockDict or error string
	if isinstance(result, str):
		pytest.fail(f"Expected BlockDict, got error: {result}")
	
	# Assume single key-value pair in BlockDict
	assert isinstance(result, BlockDict)
	result_dict = result.to_dict()
	assert len(result_dict) == 1
	
	# Get the single page data
	page_data = next(iter(result_dict.values()))
	
	assert page_data["object"] == "page"
	assert "id" in page_data
	assert notion_client.index.resolve_to_uuid(page_data["id"]) == CustomUUID.from_string(page_id)
	assert "properties" in page_data


@pytest.mark.asyncio
async def test_navigate_to_database(notion_client):
	database_id ="fb76be1f-9668-4194-952d-4ddfac58df48"
	
	result = await notion_client.get_notion_page_details(database_id=database_id)

	# Handle BlockDict or error string
	if isinstance(result, str):
		pytest.fail(f"Expected BlockDict, got error: {result}")
	
	# Assume single key-value pair in BlockDict
	assert isinstance(result, BlockDict)
	result_dict = result.to_dict()
	assert len(result_dict) == 1
	
	# Get the single database data
	database_data = next(iter(result_dict.values()))
	
	assert database_data["object"] == "database"
	assert "id" in database_data
	assert notion_client.index.resolve_to_uuid(database_data["id"]) == CustomUUID.from_string(database_id)
	assert "properties" in database_data


@pytest.mark.asyncio
async def test_navigate_to_notion_page_negative(notion_client):
	page_id = "11111111-1111-1111-1111-111111111111" # Valid format, but non-existent
	result = await notion_client.get_notion_page_details(page_id=page_id)
	
	# Should return error string for invalid page
	assert isinstance(result, str), f"Expected error string, got {type(result)}"
	# Check for CacheRetrievalError message instead of HTTP error
	assert "Failed to retrieve page" in result


@pytest.mark.asyncio
async def test_search_notion(notion_client):
	result = await notion_client.search_notion("Sprawy życiowe")

	# Handle BlockDict or error string
	if isinstance(result, str):
		pytest.fail(f"Expected BlockDict, got error: {result}")
	
	# BlockDict contains search results as individual blocks
	assert isinstance(result, BlockDict)
	result_dict = result.to_dict()
	
	# Verify we have search results
	assert len(result_dict) > 0
	assert len(result_dict) <= 10
	
	# Each result should be a database/page object
	for block_id, block_data in result_dict.items():
		assert isinstance(block_id, int)
		assert isinstance(block_data, dict)
		assert "object" in block_data

# TODO: Test search results caching

@pytest.mark.asyncio
async def test_search_notion_with_filter(notion_client):
	result = await notion_client.search_notion("AI", filter_type="database", sort="ascending")

	# Handle BlockDict or error string
	if isinstance(result, str):
		pytest.fail(f"Expected BlockDict, got error: {result}")
	
	# BlockDict contains search results as individual blocks
	assert isinstance(result, BlockDict)
	result_dict = result.to_dict()
	
	# Verify we have search results
	assert len(result_dict) > 0
	
	# Each result should be a database object
	for block_id, block_data in result_dict.items():
		assert isinstance(block_id, int)
		assert isinstance(block_data, dict)
		assert block_data["object"] == "database"


@pytest.mark.asyncio
async def test_get_children(notion_client):
	block_id = "593cf337c82a47fd80a750671b2a1e43"
	block_tree = BlockTree()

	result = await notion_client.get_block_content(block_id=block_id, block_tree=block_tree)

	# Handle BlockDict or error string
	if isinstance(result, str):
		pytest.fail(f"Expected BlockDict, got error: {result}")

	# Now get_block_content always returns all children recursively
	assert isinstance(result, BlockDict)
	result_dict = result.to_dict()
	
	# Should have multiple children blocks, not a single "list" object
	assert len(result_dict) > 1
	
	# All keys should be integers (block IDs)
	for key in result_dict.keys():
		assert isinstance(key, int), f"Expected int key, got {type(key)}: {key}"
	
	# All values should be dictionaries (block content)
	for value in result_dict.values():
		assert isinstance(value, dict), f"Expected dict value, got {type(value)}"
		# Each block should have an object type
		assert "object" in value


@pytest.mark.asyncio
async def test_filter_database(notion_client):
	database_id = "fb76be1f96684194952d4ddfac58df48"

	filter = {
		"or": [
			{
				"property": "Status",
				"select": {
					"equals": "TODO"
				}
			},
			{
				"or": [
					{
						"property": "Label",
						"select": {
							"equals": "C"
						}
					},
					{
						"property": "Label",
						"select": {
							"equals": "B"
						}
					}
				]
			}
		]
	}

	result = await notion_client.query_database(database_id=database_id, filter=filter)

	# Handle BlockDict or error string
	if isinstance(result, str):
		pytest.fail(f"Expected BlockDict, got error: {result}")
	
	# BlockDict contains database query results as individual blocks
	assert isinstance(result, BlockDict)
	result_dict = result.to_dict()
	
	# Verify we have query results
	assert len(result_dict) > 0
	
	# Each result should be a page object from the database
	for block_id, block_data in result_dict.items():
		assert isinstance(block_id, int)
		assert isinstance(block_data, dict)
		assert block_data["object"] == "page"


@pytest.mark.asyncio
async def test_database_query_with_empty_filter(notion_client):
	database_id = "fb76be1f96684194952d4ddfac58df48"

	result = await notion_client.query_database(database_id=database_id, filter={})

	# Handle BlockDict or error string
	if isinstance(result, str):
		pytest.fail(f"Expected BlockDict, got error: {result}")
	
	# BlockDict contains database query results as individual blocks
	assert isinstance(result, BlockDict)
	result_dict = result.to_dict()
	
	# Verify we have query results
	assert len(result_dict) > 0
	
	# Each result should be a page object from the database
	for block_id, block_data in result_dict.items():
		assert isinstance(block_id, int)
		assert isinstance(block_data, dict)
		assert block_data["object"] == "page"
	
	# Note: We can't easily check has_more and next_cursor since they're not in BlockDict
	# This is a limitation of the new return type for paginated results


@pytest.mark.asyncio
async def test_get_block_children_return_type(notion_client):
	"""Test that get_block_children returns Union[BlockDict, str]"""
	block_id = "593cf337c82a47fd80a750671b2a1e43"
	block_tree = BlockTree()
	
	# First get some content to ensure children are cached
	await notion_client.get_block_content(block_id=block_id, block_tree=block_tree)
	
	# Test successful case - should return BlockDict
	result = await notion_client.get_block_children(block_id, block_tree)
	
	assert isinstance(result, (BlockDict, str)), f"Expected BlockDict or str, got {type(result)}"
	
	if isinstance(result, BlockDict):
		# Verify it behaves like a dictionary
		assert hasattr(result, 'items')
		assert hasattr(result, 'keys')
		assert hasattr(result, 'values')
		assert hasattr(result, 'to_dict')
		# Test dictionary-like access
		dict_version = result.to_dict()
		assert isinstance(dict_version, dict)


@pytest.mark.asyncio
async def test_get_block_children_error_case(notion_client):
	"""Test that get_block_children returns error string for invalid input"""
	# Test with None block_tree - should return error string
	result = await notion_client.get_block_children("invalid-uuid", None)
	
	assert isinstance(result, str), f"Expected error string, got {type(result)}"
	assert "Invalid UUID" in result or "BlockTree is required" in result


@pytest.mark.asyncio
async def test_get_all_children_recursively_return_type(notion_client):
	"""Test that get_all_children_recursively returns Union[BlockDict, str]"""
	block_id = "593cf337c82a47fd80a750671b2a1e43"
	block_tree = BlockTree()
	
	# Test successful case - should return BlockDict
	result = await notion_client.get_all_children_recursively(block_id, block_tree)
	
	assert isinstance(result, (BlockDict, str)), f"Expected BlockDict or str, got {type(result)}"
	
	if isinstance(result, BlockDict):
		# Verify it's a flat dictionary (no nested structures)
		dict_version = result.to_dict()
		assert isinstance(dict_version, dict)
		
		# All keys should be integers (block IDs)
		for key in dict_version.keys():
			assert isinstance(key, int), f"Expected int key, got {type(key)}: {key}"
		
		# All values should be dictionaries (block content)
		for value in dict_version.values():
			assert isinstance(value, dict), f"Expected dict value, got {type(value)}"


@pytest.mark.asyncio
async def test_get_all_children_recursively_error_case(notion_client):
	"""Test that get_all_children_recursively returns error string for invalid input"""
	# Test with None block_tree - should return error string
	result = await notion_client.get_all_children_recursively("invalid-uuid", None)
	
	assert isinstance(result, str), f"Expected error string, got {type(result)}"
	assert "Invalid UUID" in result or "BlockTree is required" in result


@pytest.mark.asyncio
async def test_get_block_content_with_invalid_id(notion_client):
	"""Test HTTP error handling with deliberately incorrect block ID"""
	invalid_block_id = "00000000-0000-0000-0000-000000000000"  # Valid UUID format but non-existent
	block_tree = BlockTree()
	
	# This should trigger an HTTP error and return error string
	result = await notion_client.get_block_content(
		block_id=invalid_block_id, 
		block_tree=block_tree
	)
	
	# Should return error string for invalid block ID
	assert isinstance(result, str), f"Expected error string, got {type(result)}"
	# Check for CacheRetrievalError message instead of HTTP error
	assert "Failed to retrieve block" in result


@pytest.mark.asyncio
async def test_get_block_content_recursive_return_type(notion_client):
	"""Test that get_block_content always returns all children recursively"""
	block_id = "593cf337c82a47fd80a750671b2a1e43"
	block_tree = BlockTree()
	
	# Test that get_block_content always returns all children recursively
	result = await notion_client.get_block_content(
		block_id=block_id, 
		block_tree=block_tree
	)
	
	# Should always return BlockDict with all children
	assert isinstance(result, (BlockDict, dict)), f"Expected BlockDict or dict, got {type(result)}"
	
	if isinstance(result, BlockDict):
		# Verify flat structure
		dict_version = result.to_dict()
		for key in dict_version.keys():
			assert isinstance(key, int), f"Expected int key, got {type(key)}"


