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

	assert result["object"] == "page"
	assert "id" in result
	assert notion_client.index.resolve_to_uuid(result["id"]) == CustomUUID.from_string(page_id)
	assert "properties" in result

@pytest.mark.asyncio
async def test_navigate_to_database(notion_client):
	database_id ="fb76be1f-9668-4194-952d-4ddfac58df48"
	
	result = await notion_client.get_notion_page_details(database_id=database_id)

	assert result["object"] == "database"
	assert "id" in result
	assert notion_client.index.resolve_to_uuid(result["id"]) == CustomUUID.from_string(database_id)
	assert "properties" in result

@pytest.mark.asyncio
async def test_navigate_to_notion_page_negative(notion_client):
	page_id = "11111111-1111-1111-1111-111111111111" # Valid format, but non-existent
	result = await notion_client.get_notion_page_details(page_id=page_id)
	
	assert isinstance(result, dict)
	# After clean_error_message, "object" key should be removed or its value None
	assert result.get("object") is None 
	assert "status" in result
	# Allow for 404 or 400 as Notion might return different codes for "not found" vs "bad request"
	# depending on how it interprets a correctly formatted but non-existent ID
	assert result["status"] in [404, 400] 
	assert "code" in result 
	assert "message" in result

@pytest.mark.asyncio
async def test_search_notion(notion_client):
	result = await notion_client.search_notion("Sprawy życiowe")

	assert result["object"] == "list"
	assert "results" in result
	assert "next_cursor" not in result
	assert "has_more" in result
	assert len(result["results"]) <= 10

# TODO: Test search results caching

@pytest.mark.asyncio
async def test_search_notion_with_filter(notion_client):
	result = await notion_client.search_notion("AI", filter_type="database", sort="ascending")

	assert result["object"] == "list"
	assert "results" in result

	for item in result["results"]:
		assert item["object"] == "database"

@pytest.mark.asyncio
async def test_get_children(notion_client):
	block_id = "593cf337c82a47fd80a750671b2a1e43"
	block_tree = BlockTree()

	result = await notion_client.get_block_content(block_id=block_id, block_tree=block_tree)

	assert result["object"] == "list"
	assert "results" in result
	assert "next_cursor" in result
	assert "has_more" in result

	if result["has_more"] == True:
		print(f"Has more: {result['has_more']}, starting cursor in children test: {result['next_cursor']}")
		start_cursor=notion_client.index.resolve_to_uuid(result["next_cursor"])
		result = await notion_client.get_block_content(block_id=block_id, start_cursor=start_cursor, block_tree=block_tree)

		assert result["object"] == "list"
		assert "results" in result

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

	assert result["object"] == "list"
	assert "results" in result

@pytest.mark.asyncio
async def test_database_query_with_empty_filter(notion_client):
	database_id = "fb76be1f96684194952d4ddfac58df48"

	result = await notion_client.query_database(database_id=database_id, filter={})

	assert result["object"] == "list"
	assert "results" in result

	if result["has_more"]:
		start_cursor=notion_client.index.resolve_to_uuid(result["next_cursor"])
		result = await notion_client.query_database(database_id=database_id, filter={}, start_cursor=start_cursor)
		assert result["object"] == "list"


