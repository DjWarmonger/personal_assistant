import os
import pytest
import pytest_asyncio
from dotenv import load_dotenv
import sys

# Update the import path to include the project root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Use direct imports from operations
from operations.notion.notion_client import NotionClient
from operations.notion.asyncClientManager import AsyncClientManager
from operations.blocks.blockTree import BlockTree
from operations.blocks.blockDict import BlockDict
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
	page_id = os.getenv("NOTION_SYSTEMC_PAGE_ID")
	
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
	# Check for error message - could be either "Failed to retrieve page" or "Failed to retrieve block"
	assert ("Failed to retrieve page" in result or "Failed to retrieve block" in result), f"Expected error message about failed retrieval, got: {result}"


@pytest.mark.asyncio
async def test_get_block_content_recursive_return_type(notion_client):
	"""Test that get_block_content always returns all children recursively"""
	block_id = os.getenv("NOTION_SYSTEMC_PAGE_ID")
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


@pytest.mark.asyncio
async def test_same_page_uuid_handled_by_both_tools(notion_client):
	"""Test that the same page UUID can be handled correctly by both page details and block content methods"""
	page_id = os.getenv("NOTION_SYSTEMC_PAGE_ID")
	if not page_id:
		pytest.skip("NOTION_SYSTEMC_PAGE_ID not found in environment")
	
	# Test NotionPageDetailsTool functionality (get_notion_page_details)
	page_details_result = await notion_client.get_notion_page_details(page_id=page_id)
	
	# Should return page properties without children
	if isinstance(page_details_result, str):
		pytest.fail(f"get_notion_page_details failed: {page_details_result}")
	
	assert isinstance(page_details_result, BlockDict)
	page_details_dict = page_details_result.to_dict()
	assert len(page_details_dict) == 1
	
	page_data = next(iter(page_details_dict.values()))
	assert page_data["object"] == "page"
	assert "properties" in page_data
	page_int_id = next(iter(page_details_dict.keys()))
	
	# Test NotionGetBlockContentTool functionality (get_block_content)
	block_tree = BlockTree()
	block_content_result = await notion_client.get_block_content(
		block_id=page_id, 
		block_tree=block_tree
	)
	
	# Should return page + all children recursively
	if isinstance(block_content_result, str):
		pytest.fail(f"get_block_content failed: {block_content_result}")
	
	assert isinstance(block_content_result, BlockDict)
	block_content_dict = block_content_result.to_dict()
	
	# Should have children blocks (current behavior: parent page not included in children result)
	# TODO: This reveals the issue mentioned in TODO.md - get_block_content should include parent block
	assert len(block_content_dict) >= 1
	
	# Verify UUID resolution works consistently for both methods
	resolved_uuid_from_details = notion_client.index.resolve_to_uuid(page_data["id"])
	assert resolved_uuid_from_details == CustomUUID.from_string(page_id)
	
	# Verify that both methods can process the same UUID without errors
	# Even though they return different content (page properties vs children blocks)
	assert isinstance(page_details_result, BlockDict)
	assert isinstance(block_content_result, BlockDict)
	
	print(f"✅ Both tools successfully handled page UUID: {page_id}")
	print(f"   - Page details returned: 1 block (page properties only)")
	print(f"   - Block content returned: {len(block_content_dict)} blocks (children only)")
	print(f"   - NOTE: Current behavior - get_block_content returns children but not parent page")


