import sys
import os
import pytest
import pytest_asyncio
from notion_client import NotionClient
from dotenv import load_dotenv
from asyncClientManager import AsyncClientManager

load_dotenv()

@pytest_asyncio.fixture
async def notion_client():
	client = NotionClient()
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
	assert notion_client.index.to_uuid(result["id"]) == notion_client.index.converter.clean_uuid(page_id)
	assert "properties" in result

@pytest.mark.asyncio
async def test_navigate_to_database(notion_client):
	database_id ="fb76be1f-9668-4194-952d-4ddfac58df48"
	
	result = await notion_client.get_notion_page_details(database_id=database_id)

	assert result["object"] == "database"
	assert "id" in result
	assert notion_client.index.to_uuid(result["id"]) == notion_client.index.converter.clean_uuid(database_id)
	assert "properties" in result

@pytest.mark.asyncio
async def test_navigate_to_notion_page_negative(notion_client):
	page_id = "invalid-page-id"
	result = await notion_client.get_notion_page_details(page_id=page_id)
	assert "status" not in result

@pytest.mark.asyncio
async def test_search_notion(notion_client):
	result = await notion_client.search_notion("Sprawy życiowe")

	assert result["object"] == "list"
	assert "results" in result
	assert "next_cursor" not in result
	assert "has_more" in result
	assert len(result["results"]) <= 10

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

	result = await notion_client.get_block_content(block_id=block_id)

	assert result["object"] == "list"
	assert "results" in result
	assert "next_cursor" in result
	assert "has_more" in result

	if result["has_more"] == True:
		print(f"Has more: {result['has_more']}, starting cursor in children test: {result['next_cursor']}")
		result = await notion_client.get_block_content(block_id=block_id, start_cursor=result["next_cursor"])

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
		result = await notion_client.query_database(database_id=database_id, filter={}, start_cursor=result["next_cursor"])
		assert result["object"] == "list"

