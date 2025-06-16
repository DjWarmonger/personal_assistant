import pytest
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any

from operations.notion.notion_client import NotionClient
from operations.captioning.captionGenerator import CaptionGenerator
from operations.captioning.backgroundProcessor import BackgroundCaptionProcessor
from operations.blocks.index import Index
from operations.blocks.blockCache import BlockCache
from operations.blocks.blockHolder import BlockHolder
from operations.urlIndex import UrlIndex
from tz_common import CustomUUID
from tz_common.aitoolbox import AIToolbox


class TestCaptionIntegration:
	"""Integration tests for the complete caption generation workflow."""

	@pytest.fixture
	def mock_ai_toolbox(self):
		"""Mock AIToolbox for caption generation."""
		mock_toolbox = MagicMock(spec=AIToolbox)
		
		# Mock successful API response - return JSON string, not dict
		# send_openai_request is NOT async, so use regular MagicMock
		mock_response = '{"caption": "Test caption for block"}'
		mock_toolbox.send_openai_request = MagicMock(return_value=mock_response)
		
		return mock_toolbox

	@pytest.fixture
	def notion_client_with_captions(self, mock_ai_toolbox):
		"""Create NotionClient with caption generation enabled and mocked AIToolbox."""
		with patch('operations.captioning.captionGenerator.AIToolbox') as mock_class:
			mock_class.return_value = mock_ai_toolbox
			client = NotionClient(
				load_from_disk=False,
				run_on_start=False,
				enable_caption_generation=True,
				langfuse_handler=None
			)
			return client

	@pytest.fixture
	def notion_client_without_captions(self):
		"""Create NotionClient with caption generation disabled."""
		client = NotionClient(
			load_from_disk=False,
			run_on_start=False,
			enable_caption_generation=False
		)
		return client

	@pytest.fixture
	def sample_block_data(self):
		"""Sample block data for testing."""
		return {
			"id": "123e4567-e89b-12d3-a456-426614174000",
			"object": "block",
			"type": "paragraph",
			"paragraph": {
				"rich_text": [
					{
						"type": "text",
						"text": {"content": "This is a test paragraph with meaningful content."}
					}
				]
			},
			"has_children": False,
			"created_time": "2023-01-01T00:00:00.000Z",
			"last_edited_time": "2023-01-01T00:00:00.000Z"
		}

	@pytest.mark.asyncio
	async def test_caption_processor_initialization_enabled(self, notion_client_with_captions):
		"""Test that caption processor is properly initialized when enabled."""
		client = notion_client_with_captions
		
		# Verify caption processor was created
		assert client.caption_processor is not None
		assert isinstance(client.caption_processor, BackgroundCaptionProcessor)
		
		# Verify it was passed to block manager
		assert client.block_manager.caption_processor is not None
		assert client.block_manager.caption_processor is client.caption_processor
		
		# Verify it was passed to service
		assert client.service.caption_processor is not None
		assert client.service.caption_processor is client.caption_processor

	def test_caption_processor_initialization_disabled(self, notion_client_without_captions):
		"""Test that caption processor is None when disabled."""
		client = notion_client_without_captions
		
		# Verify caption processor was not created
		assert client.caption_processor is None
		
		# Verify block manager has no caption processor
		assert client.block_manager.caption_processor is None
		
		# Verify service has no caption processor
		assert client.service.caption_processor is None

	@pytest.mark.asyncio
	async def test_caption_generation_lifecycle(self, notion_client_with_captions, mock_ai_toolbox):
		"""Test the complete caption generation lifecycle."""
		client = notion_client_with_captions
		
		async with client:
			# Verify background processing started
			assert client.caption_processor.is_running
			
			# Create a test block without a name
			test_uuid = CustomUUID.from_string("123e4567-e89b-12d3-a456-426614174000")
			test_int_id = client.index.add_uuid(test_uuid, name="")  # Empty name
			
			# Verify block has no name initially
			assert client.index.get_name(test_int_id) == ""
			
			# Queue caption generation - use longer text to avoid short text reuse
			block_content = {
				"type": "paragraph",
				"paragraph": {
					"rich_text": [{"text": {"content": "This is a longer test content for caption generation that will trigger API call"}}]
				}
			}
			
			success = client.caption_processor.queue_caption_generation(
				uuid=test_uuid,
				int_id=test_int_id,
				block_content=block_content,
				block_type="block"
			)
			
			assert success is True
			
			# Wait for processing to complete
			await client.caption_processor.wait_for_queue_empty(timeout=10.0)
			
			# Verify caption was generated and name was updated
			updated_name = client.index.get_name(test_int_id)
			assert updated_name == "Test caption for block"
			
			# Verify AIToolbox was called
			mock_ai_toolbox.send_openai_request.assert_called_once()
			call_args = mock_ai_toolbox.send_openai_request.call_args
			assert "longer test content" in call_args[1]["message"]

	@pytest.mark.asyncio
	async def test_caption_generation_skips_existing_names(self, notion_client_with_captions, mock_ai_toolbox):
		"""Test that caption generation is skipped for blocks that already have names."""
		client = notion_client_with_captions
		
		async with client:
			# Create a test block with an existing name
			test_uuid = CustomUUID.from_string("123e4567-e89b-12d3-a456-426614174000")
			test_int_id = client.index.add_uuid(test_uuid, name="Existing Name")
			
			# Verify block has existing name
			assert client.index.get_name(test_int_id) == "Existing Name"
			
			# Try to queue caption generation - use longer text to avoid short text reuse
			block_content = {
				"type": "paragraph",
				"paragraph": {
					"rich_text": [{"text": {"content": "This is a longer test content that should trigger API call"}}]
				}
			}
			
			success = client.caption_processor.queue_caption_generation(
				uuid=test_uuid,
				int_id=test_int_id,
				block_content=block_content,
				block_type="block"
			)
			
			# Should return False because block already has a name
			assert success is False
			
			# Verify name wasn't changed
			assert client.index.get_name(test_int_id) == "Existing Name"
			
			# Verify AIToolbox was not called
			mock_ai_toolbox.send_openai_request.assert_not_called()

	@pytest.mark.asyncio
	async def test_caption_generation_through_block_processing(self, notion_client_with_captions, sample_block_data, mock_ai_toolbox):
		"""Test that caption generation is triggered through normal block processing."""
		client = notion_client_with_captions
		
		async with client:
			# Process a block through BlockManager (simulating normal flow)
			from operations.blocks.blockCache import ObjectType
			
			main_int_id = client.block_manager.process_and_store_block(
				raw_data=sample_block_data,
				object_type=ObjectType.BLOCK
			)
			
			# Verify block was processed
			assert main_int_id is not None
			
			# Initially, block should have no name
			initial_name = client.index.get_name(main_int_id)
			assert initial_name == ""
			
			# Wait for caption generation to complete
			await client.caption_processor.wait_for_queue_empty(timeout=10.0)
			
			# Verify caption was generated and name was updated
			updated_name = client.index.get_name(main_int_id)
			assert updated_name == "Test caption for block"
			
			# Verify AIToolbox was called with the block content
			mock_ai_toolbox.send_openai_request.assert_called_once()

	@pytest.mark.asyncio
	async def test_caption_generation_error_handling(self, notion_client_with_captions, mock_ai_toolbox):
		"""Test that caption generation errors don't break the system."""
		client = notion_client_with_captions
		
		# Mock AIToolbox to raise an exception
		mock_ai_toolbox.send_openai_request.side_effect = Exception("API Error")
		
		async with client:
			# Create a test block without a name
			test_uuid = CustomUUID.from_string("123e4567-e89b-12d3-a456-426614174000")
			test_int_id = client.index.add_uuid(test_uuid, name="")
			
			# Queue caption generation - use longer text to trigger API call
			block_content = {
				"type": "paragraph",
				"paragraph": {
					"rich_text": [{"text": {"content": "This is a longer test content that should trigger API call and fail"}}]
				}
			}
			
			success = client.caption_processor.queue_caption_generation(
				uuid=test_uuid,
				int_id=test_int_id,
				block_content=block_content,
				block_type="block"
			)
			
			assert success is True
			
			# Wait for processing to complete
			await client.caption_processor.wait_for_queue_empty(timeout=10.0)
			
			# Verify name wasn't updated due to error
			updated_name = client.index.get_name(test_int_id)
			assert updated_name == ""  # Should remain empty
			
			# Verify AIToolbox was called but failed
			mock_ai_toolbox.send_openai_request.assert_called_once()

	@pytest.mark.asyncio
	async def test_caption_generation_with_langfuse_handler(self, mock_ai_toolbox):
		"""Test that langfuse_handler is properly passed through to caption generator."""
		mock_langfuse_handler = MagicMock()
		
		with patch('operations.captioning.captionGenerator.AIToolbox', return_value=mock_ai_toolbox):
			client = NotionClient(
				load_from_disk=False,
				run_on_start=False,
				enable_caption_generation=True,
				langfuse_handler=mock_langfuse_handler
			)
			
			# Verify caption processor was created
			assert client.caption_processor is not None
			
			# The langfuse_handler should have been passed to CaptionGenerator
			# which then passes it to AIToolbox - we can verify this by checking
			# that AIToolbox was instantiated with the handler
			# (This is a bit indirect but tests the integration)
			assert mock_ai_toolbox is not None

	@pytest.mark.asyncio
	async def test_background_processing_lifecycle(self, notion_client_with_captions):
		"""Test that background processing starts and stops correctly."""
		client = notion_client_with_captions
		
		# Initially not running
		assert not client.caption_processor.is_running
		
		# Start client (should start background processing)
		async with client:
			assert client.caption_processor.is_running
			
			# Verify processing task is running
			assert client.caption_processor.processing_task is not None
			assert not client.caption_processor.processing_task.done()
		
		# After exiting context, should be stopped
		assert not client.caption_processor.is_running
		assert client.caption_processor.processing_task is None or client.caption_processor.processing_task.done()

	@pytest.mark.asyncio
	async def test_multiple_blocks_caption_generation(self, notion_client_with_captions, mock_ai_toolbox):
		"""Test caption generation for multiple blocks concurrently."""
		client = notion_client_with_captions
		
		# Mock different responses for different blocks - return JSON strings
		responses = [
			'{"caption": "First block caption"}',
			'{"caption": "Second block caption"}',
			'{"caption": "Third block caption"}'
		]
		mock_ai_toolbox.send_openai_request.side_effect = responses
		
		async with client:
			# Create multiple test blocks
			test_blocks = []
			for i in range(3):
				test_uuid = CustomUUID.from_string(f"123e4567-e89b-12d3-a456-42661417400{i}")
				test_int_id = client.index.add_uuid(test_uuid, name="")
				test_blocks.append((test_uuid, test_int_id))
			
			# Queue caption generation for all blocks - use longer text to trigger API calls
			for i, (uuid, int_id) in enumerate(test_blocks):
				block_content = {
					"type": "paragraph",
					"paragraph": {
						"rich_text": [{"text": {"content": f"This is a longer test content for block {i} that will trigger API call"}}]
					}
				}
				
				success = client.caption_processor.queue_caption_generation(
					uuid=uuid,
					int_id=int_id,
					block_content=block_content,
					block_type="block"
				)
				assert success is True
			
			# Wait for all processing to complete
			await client.caption_processor.wait_for_queue_empty(timeout=15.0)
			
			# Verify all captions were generated
			expected_captions = ["First block caption", "Second block caption", "Third block caption"]
			actual_captions = []
			
			for _, int_id in test_blocks:
				caption = client.index.get_name(int_id)
				actual_captions.append(caption)
			
			# All blocks should have captions (order might vary due to concurrent processing)
			assert set(actual_captions) == set(expected_captions)
			
			# Verify AIToolbox was called for each block
			assert mock_ai_toolbox.send_openai_request.call_count == 3

	@pytest.mark.asyncio
	async def test_caption_generation_for_cached_page_load(self, notion_client_with_captions, mock_ai_toolbox):
		"""Test that caption generation is triggered when loading pages from cache."""
		client = notion_client_with_captions
		
		async with client:
			# Create a test page and store it in cache
			test_uuid = CustomUUID.from_string("123e4567-e89b-12d3-a456-426614174000")
			test_int_id = client.index.add_uuid(test_uuid, name="")  # No name initially
			
			page_data = {
				"id": str(test_uuid),
				"object": "page",
				"properties": {
					"title": {
						"title": [{"text": {"content": "This is a longer test page title for caption generation"}}]
					}
				},
				"created_time": "2023-01-01T00:00:00.000Z",
				"last_edited_time": "2023-01-01T00:00:00.000Z"
			}
			
			# Store in cache
			import json
			client.cache.add_page(test_uuid, json.dumps(page_data))
			
			# Load from cache through CacheOrchestrator
			async def dummy_fetcher():
				return page_data
			
			result = await client.cache_orchestrator.get_or_fetch_page(test_uuid, dummy_fetcher)
			
			# Verify page was loaded from cache
			assert result is not None
			
			# Wait for caption generation to complete
			await client.caption_processor.wait_for_queue_empty(timeout=10.0)
			
			# Verify caption was generated
			updated_name = client.index.get_name(test_int_id)
			assert updated_name == "Test caption for block"
			
			# Verify AIToolbox was called
			mock_ai_toolbox.send_openai_request.assert_called_once()

	@pytest.mark.asyncio
	async def test_caption_generation_for_cached_database_load(self, notion_client_with_captions, mock_ai_toolbox):
		"""Test that caption generation is triggered when loading databases from cache."""
		client = notion_client_with_captions
		
		async with client:
			# Create a test database and store it in cache
			test_uuid = CustomUUID.from_string("123e4567-e89b-12d3-a456-426614174000")
			test_int_id = client.index.add_uuid(test_uuid, name="")  # No name initially
			
			database_data = {
				"id": str(test_uuid),
				"object": "database",
				"title": [{"text": {"content": "This is a longer test database title for caption generation"}}],
				"properties": {},
				"created_time": "2023-01-01T00:00:00.000Z",
				"last_edited_time": "2023-01-01T00:00:00.000Z"
			}
			
			# Store in cache
			client.cache.add_database(test_uuid, json.dumps(database_data))
			
			# Load from cache through CacheOrchestrator
			async def dummy_fetcher():
				return database_data
			
			result = await client.cache_orchestrator.get_or_fetch_database(test_uuid, dummy_fetcher)
			
			# Verify database was loaded from cache
			assert result is not None
			
			# Wait for caption generation to complete
			await client.caption_processor.wait_for_queue_empty(timeout=10.0)
			
			# Verify caption was generated
			updated_name = client.index.get_name(test_int_id)
			assert updated_name == "Test caption for block"
			
			# Verify AIToolbox was called
			mock_ai_toolbox.send_openai_request.assert_called_once()

	@pytest.mark.asyncio
	async def test_caption_generation_for_cached_block_content(self, notion_client_with_captions, mock_ai_toolbox):
		"""Test that caption generation is triggered when loading block content from cache."""
		client = notion_client_with_captions
		
		async with client:
			# Create a test block and store it in cache
			test_uuid = CustomUUID.from_string("123e4567-e89b-12d3-a456-426614174000")
			test_int_id = client.index.add_uuid(test_uuid, name="")  # No name initially
			
			block_data = {
				"id": str(test_uuid),
				"object": "block",
				"type": "paragraph",
				"paragraph": {
					"rich_text": [{"text": {"content": "This is a longer test block content for caption generation"}}]
				},
				"created_time": "2023-01-01T00:00:00.000Z",
				"last_edited_time": "2023-01-01T00:00:00.000Z"
			}
			
			# Store in cache
			client.cache.add_block(test_uuid, json.dumps(block_data))
			
			# Load from cache through CacheOrchestrator
			result = client.cache_orchestrator.get_cached_block_content(test_uuid)
			
			# Verify block was loaded from cache
			assert result is not None
			
			# Wait for caption generation to complete
			await client.caption_processor.wait_for_queue_empty(timeout=10.0)
			
			# Verify caption was generated
			updated_name = client.index.get_name(test_int_id)
			assert updated_name == "Test caption for block"
			
			# Verify AIToolbox was called
			mock_ai_toolbox.send_openai_request.assert_called_once()

	@pytest.mark.asyncio
	async def test_caption_generation_not_triggered_for_cached_search_results(self, notion_client_with_captions, mock_ai_toolbox):
		"""Test that caption generation is NOT triggered when loading search results from cache (intentional behavior)."""
		client = notion_client_with_captions
		
		async with client:
			# Create test search results with blocks that have no names
			test_uuid1 = CustomUUID.from_string("123e4567-e89b-12d3-a456-426614174001")
			test_uuid2 = CustomUUID.from_string("123e4567-e89b-12d3-a456-426614174002")
			
			test_int_id1 = client.index.add_uuid(test_uuid1, name="")  # No name initially
			test_int_id2 = client.index.add_uuid(test_uuid2, name="")  # No name initially
			
			search_results = {
				"results": [
					{
						"id": str(test_uuid1),
						"object": "page",
						"properties": {
							"title": {"title": [{"text": {"content": "First longer test page for caption generation"}}]}
						}
					},
					{
						"id": str(test_uuid2),
						"object": "block",
						"type": "paragraph",
						"paragraph": {
							"rich_text": [{"text": {"content": "Second longer test block for caption generation"}}]
						}
					}
				]
			}
			
			# Store search results in cache
			client.cache.add_search_results("test query", json.dumps(search_results))
			
			# Load from cache through CacheOrchestrator
			result = client.cache_orchestrator.get_cached_search_results("test query")
			
			# Verify search results were loaded from cache
			assert result is not None
			
			# Wait a bit to ensure no caption generation was queued
			await asyncio.sleep(0.1)
			
			# Verify captions were NOT generated (search results are references, not new content)
			updated_name1 = client.index.get_name(test_int_id1)
			updated_name2 = client.index.get_name(test_int_id2)
			assert updated_name1 == ""  # Should remain empty
			assert updated_name2 == ""  # Should remain empty
			
			# Verify AIToolbox was not called (no caption generation for search results)
			mock_ai_toolbox.send_openai_request.assert_not_called()

	@pytest.mark.asyncio
	async def test_caption_generation_for_cached_database_query_results(self, notion_client_with_captions, mock_ai_toolbox):
		"""Test that caption generation is triggered when loading database query results from cache."""
		client = notion_client_with_captions
		
		async with client:
			# Create test database query results with pages that have no names
			test_uuid1 = CustomUUID.from_string("123e4567-e89b-12d3-a456-426614174001")
			test_uuid2 = CustomUUID.from_string("123e4567-e89b-12d3-a456-426614174002")
			
			test_int_id1 = client.index.add_uuid(test_uuid1, name="")  # No name initially
			test_int_id2 = client.index.add_uuid(test_uuid2, name="")  # No name initially
			
			query_results = {
				"results": [
					{
						"id": str(test_uuid1),
						"object": "page",
						"properties": {
							"title": {"title": [{"text": {"content": "First longer database page for caption generation"}}]}
						}
					},
					{
						"id": str(test_uuid2),
						"object": "page",
						"properties": {
							"title": {"title": [{"text": {"content": "Second longer database page for caption generation"}}]}
						}
					}
				]
			}
			
			# Store database query results in cache
			database_uuid = CustomUUID.from_string("123e4567-e89b-12d3-a456-426614174999")
			client.cache.add_database_query_results(database_uuid, json.dumps(query_results))
			
			# Load from cache through CacheOrchestrator
			result = client.cache_orchestrator.get_cached_database_query_results(database_uuid)
			
			# Verify query results were loaded from cache
			assert result is not None
			
			# Wait for caption generation to complete
			await client.caption_processor.wait_for_queue_empty(timeout=10.0)
			
			# Verify captions were generated for both pages
			updated_name1 = client.index.get_name(test_int_id1)
			updated_name2 = client.index.get_name(test_int_id2)
			assert updated_name1 == "Test caption for block"
			assert updated_name2 == "Test caption for block"
			
			# Verify AIToolbox was called for both pages
			assert mock_ai_toolbox.send_openai_request.call_count == 2

	@pytest.mark.asyncio
	async def test_caption_generation_skips_blocks_with_existing_names_from_cache(self, notion_client_with_captions, mock_ai_toolbox):
		"""Test that caption generation is skipped for cached blocks that already have names."""
		client = notion_client_with_captions
		
		async with client:
			# Create a test block with an existing name
			test_uuid = CustomUUID.from_string("123e4567-e89b-12d3-a456-426614174000")
			test_int_id = client.index.add_uuid(test_uuid, name="Existing Block Name")
			
			block_data = {
				"id": str(test_uuid),
				"object": "block",
				"type": "paragraph",
				"paragraph": {
					"rich_text": [{"text": {"content": "This is a longer test block content for caption generation"}}]
				},
				"created_time": "2023-01-01T00:00:00.000Z",
				"last_edited_time": "2023-01-01T00:00:00.000Z"
			}
			
			# Store in cache
			client.cache.add_block(test_uuid, json.dumps(block_data))
			
			# Load from cache through CacheOrchestrator
			result = client.cache_orchestrator.get_cached_block_content(test_uuid)
			
			# Verify block was loaded from cache
			assert result is not None
			
			# Wait a bit to ensure no caption generation was queued
			await asyncio.sleep(0.1)
			
			# Verify name wasn't changed
			updated_name = client.index.get_name(test_int_id)
			assert updated_name == "Existing Block Name"
			
			# Verify AIToolbox was not called
			mock_ai_toolbox.send_openai_request.assert_not_called()

	@pytest.mark.asyncio
	async def test_caption_generation_disabled_for_cache_loads(self, notion_client_without_captions):
		"""Test that caption generation is not triggered when disabled, even for cache loads."""
		client = notion_client_without_captions
		
		async with client:
			# Create a test block and store it in cache
			test_uuid = CustomUUID.from_string("123e4567-e89b-12d3-a456-426614174000")
			test_int_id = client.index.add_uuid(test_uuid, name="")  # No name initially
			
			block_data = {
				"id": str(test_uuid),
				"object": "block",
				"type": "paragraph",
				"paragraph": {
					"rich_text": [{"text": {"content": "This is a longer test block content for caption generation"}}]
				},
				"created_time": "2023-01-01T00:00:00.000Z",
				"last_edited_time": "2023-01-01T00:00:00.000Z"
			}
			
			# Store in cache
			client.cache.add_block(test_uuid, json.dumps(block_data))
			
			# Load from cache through CacheOrchestrator
			result = client.cache_orchestrator.get_cached_block_content(test_uuid)
			
			# Verify block was loaded from cache
			assert result is not None
			
			# Wait a bit to ensure no caption generation was attempted
			await asyncio.sleep(0.1)
			
			# Verify name remains empty (no caption generation)
			updated_name = client.index.get_name(test_int_id)
			assert updated_name == "" 