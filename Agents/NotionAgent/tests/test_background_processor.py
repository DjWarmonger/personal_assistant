import asyncio
import sys
import os
import pytest
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any

# Update the import path to include the project root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from operations.captioning.backgroundProcessor import BackgroundCaptionProcessor, CaptionTask
from operations.captioning.captionGenerator import CaptionGenerator
from operations.blocks.blockHolder import BlockHolder
from operations.blocks.index import Index
from operations.urlIndex import UrlIndex
from tz_common import CustomUUID


class TestBackgroundCaptionProcessor:

	# Test data constants
	TEST_UUID_1 = "123e4567-e89b-12d3-a456-426614174000"
	TEST_UUID_2 = "87654321-4321-4321-4321-210987654321"
	
	# Common test data
	TEST_BLOCK_CONTENT = {"type": "paragraph", "content": "test"}
	TEST_BLOCK_TYPE = "block"
	TEST_CAPTION = "Test Caption"
	EXISTING_NAME = "Existing Name"
	
	# Test configuration
	TEST_QUEUE_SIZE = 10
	TEST_BATCH_SIZE = 3
	TEST_MAX_CONCURRENT = 2

	@classmethod
	def setup_class(cls):
		"""Set up test fixtures once for the entire test class."""
		# Create shared dependencies
		cls.url_index = UrlIndex()
		cls.block_holder = BlockHolder(cls.url_index)

	def setup_method(self):
		"""Set up test fixtures before each test method."""
		# Create mock dependencies
		self.mock_caption_generator = Mock(spec=CaptionGenerator)
		self.mock_index = Mock(spec=Index)
		
		# Create test UUIDs
		self.test_uuid_1 = CustomUUID.from_string(self.TEST_UUID_1)
		self.test_uuid_2 = CustomUUID.from_string(self.TEST_UUID_2)
		
		# Create processor with small queue for testing
		self.processor = BackgroundCaptionProcessor(
			caption_generator=self.mock_caption_generator,
			index=self.mock_index,
			max_queue_size=self.TEST_QUEUE_SIZE,
			batch_size=self.TEST_BATCH_SIZE,
			max_concurrent=self.TEST_MAX_CONCURRENT
		)

	def teardown_method(self):
		"""Clean up after each test."""
		# Ensure processor is stopped
		if self.processor.is_running:
			asyncio.create_task(self.processor.stop_background_processing())

	def test_init(self):
		"""Test processor initialization."""
		assert self.processor.caption_generator == self.mock_caption_generator
		assert self.processor.index == self.mock_index
		assert self.processor.max_queue_size == self.TEST_QUEUE_SIZE
		assert self.processor.batch_size == self.TEST_BATCH_SIZE
		assert self.processor.max_concurrent == self.TEST_MAX_CONCURRENT
		assert not self.processor.is_running
		assert not self.processor.is_shutting_down
		assert self.processor.task_queue.qsize() == 0

	def test_queue_caption_generation_success(self):
		"""Test successful queuing of caption generation task."""
		# Setup
		self.mock_index.get_name.return_value = ""  # No existing name
		
		# Test
		result = self.processor.queue_caption_generation(
			uuid=self.test_uuid_1,
			int_id=1,
			block_content=self.TEST_BLOCK_CONTENT,
			block_type=self.TEST_BLOCK_TYPE
		)
		
		# Verify
		assert result is True
		assert self.processor.task_queue.qsize() == 1
		self.mock_index.get_name.assert_called_once_with(1)

	def test_queue_caption_generation_existing_name(self):
		"""Test skipping caption generation when name already exists."""
		# Setup
		self.mock_index.get_name.return_value = self.EXISTING_NAME
		
		# Test
		result = self.processor.queue_caption_generation(
			uuid=self.test_uuid_1,
			int_id=1,
			block_content=self.TEST_BLOCK_CONTENT,
			block_type=self.TEST_BLOCK_TYPE
		)
		
		# Verify
		assert result is False
		assert self.processor.task_queue.qsize() == 0

	def test_queue_caption_generation_shutting_down(self):
		"""Test skipping caption generation when processor is shutting down."""
		# Setup
		self.processor.is_shutting_down = True
		
		# Test
		result = self.processor.queue_caption_generation(
			uuid=self.test_uuid_1,
			int_id=1,
			block_content=self.TEST_BLOCK_CONTENT,
			block_type=self.TEST_BLOCK_TYPE
		)
		
		# Verify
		assert result is False
		assert self.processor.task_queue.qsize() == 0

	def test_queue_caption_generation_queue_full(self):
		"""Test handling of full queue."""
		# Setup - fill the queue
		self.mock_index.get_name.return_value = ""
		
		# Fill queue to capacity
		for i in range(self.TEST_QUEUE_SIZE):
			self.processor.queue_caption_generation(
				uuid=self.test_uuid_1,
				int_id=i,
				block_content={"content": f"test{i}"},
				block_type=self.TEST_BLOCK_TYPE
			)
		
		# Test - try to add one more
		result = self.processor.queue_caption_generation(
			uuid=self.test_uuid_1,
			int_id=99,
			block_content={"content": "overflow"},
			block_type=self.TEST_BLOCK_TYPE
		)
		
		# Verify
		assert result is False
		assert self.processor.task_queue.qsize() == self.TEST_QUEUE_SIZE

	@pytest.mark.asyncio
	async def test_start_stop_background_processing(self):
		"""Test starting and stopping background processing."""
		# Test start
		await self.processor.start_background_processing()
		assert self.processor.is_running is True
		assert self.processor.processing_task is not None
		
		# Test stop
		await self.processor.stop_background_processing()
		assert self.processor.is_running is False
		assert self.processor.processing_task is None

	@pytest.mark.asyncio
	async def test_start_already_running(self):
		"""Test starting processor when already running."""
		# Start first time
		await self.processor.start_background_processing()
		first_task = self.processor.processing_task
		
		# Try to start again
		await self.processor.start_background_processing()
		
		# Should be the same task
		assert self.processor.processing_task == first_task
		
		# Cleanup
		await self.processor.stop_background_processing()

	@pytest.mark.asyncio
	async def test_stop_not_running(self):
		"""Test stopping processor when not running."""
		# Should not raise any errors
		await self.processor.stop_background_processing()
		assert self.processor.is_running is False

	@pytest.mark.asyncio
	async def test_process_single_caption_success(self):
		"""Test processing a single caption successfully."""
		# Setup
		self.mock_caption_generator.generate_caption_async = AsyncMock(return_value=self.TEST_CAPTION)
		self.mock_index.update_name_if_empty.return_value = True
		
		task = CaptionTask(
			uuid=self.test_uuid_1,
			int_id=1,
			block_content=self.TEST_BLOCK_CONTENT,
			block_type=self.TEST_BLOCK_TYPE
		)
		
		# Test
		await self.processor._process_single_caption(task)
		
		# Verify
		self.mock_caption_generator.generate_caption_async.assert_called_once_with(
			self.TEST_BLOCK_CONTENT, self.TEST_BLOCK_TYPE
		)
		self.mock_index.update_name_if_empty.assert_called_once_with(1, self.TEST_CAPTION)

	@pytest.mark.asyncio
	async def test_process_single_caption_name_exists(self):
		"""Test processing caption when name already exists."""
		# Setup
		self.mock_caption_generator.generate_caption_async = AsyncMock(return_value=self.TEST_CAPTION)
		self.mock_index.update_name_if_empty.return_value = False  # Name already exists
		
		task = CaptionTask(
			uuid=self.test_uuid_1,
			int_id=1,
			block_content=self.TEST_BLOCK_CONTENT,
			block_type=self.TEST_BLOCK_TYPE
		)
		
		# Test
		await self.processor._process_single_caption(task)
		
		# Verify - just check that the method completed without error
		pass

	@pytest.mark.asyncio
	async def test_process_single_caption_generation_failed(self):
		"""Test processing when caption generation fails."""
		# Setup
		self.mock_caption_generator.generate_caption_async = AsyncMock(return_value=None)
		
		task = CaptionTask(
			uuid=self.test_uuid_1,
			int_id=1,
			block_content=self.TEST_BLOCK_CONTENT,
			block_type=self.TEST_BLOCK_TYPE
		)
		
		# Test
		await self.processor._process_single_caption(task)
		
		# Verify
		self.mock_index.update_name_if_empty.assert_not_called()

	@pytest.mark.asyncio
	async def test_process_single_caption_exception(self):
		"""Test processing when an exception occurs."""
		# Setup
		self.mock_caption_generator.generate_caption_async = AsyncMock(
			side_effect=Exception("Test error")
		)
		
		task = CaptionTask(
			uuid=self.test_uuid_1,
			int_id=1,
			block_content=self.TEST_BLOCK_CONTENT,
			block_type=self.TEST_BLOCK_TYPE
		)
		
		# Test
		await self.processor._process_single_caption(task)
		
		# Verify - just check that the method completed without error
		pass

	@pytest.mark.asyncio
	async def test_collect_batch_empty_queue(self):
		"""Test collecting batch from empty queue."""
		# Test
		batch = await self.processor._collect_batch()
		
		# Verify
		assert batch == []

	@pytest.mark.asyncio
	async def test_collect_batch_with_tasks(self):
		"""Test collecting batch with tasks in queue."""
		# Setup - add tasks to queue
		self.mock_index.get_name.return_value = ""
		
		for i in range(5):
			self.processor.queue_caption_generation(
				uuid=self.test_uuid_1,
				int_id=i,
				block_content={"content": f"test{i}"},
				block_type=self.TEST_BLOCK_TYPE
			)
		
		# Test
		batch = await self.processor._collect_batch()
		
		# Verify
		assert len(batch) == self.TEST_BATCH_SIZE

	@pytest.mark.asyncio
	async def test_process_batch_empty(self):
		"""Test processing empty batch."""
		# Test - should not raise any errors
		await self.processor._process_batch([])

	@pytest.mark.asyncio
	async def test_process_batch_with_tasks(self):
		"""Test processing batch with multiple tasks."""
		# Setup
		self.mock_caption_generator.generate_caption_async = AsyncMock(return_value="Caption")
		self.mock_index.update_name_if_empty.return_value = True
		
		tasks = [
			CaptionTask(uuid=self.test_uuid_1, int_id=i, block_content={"content": f"test{i}"}, block_type=self.TEST_BLOCK_TYPE)
			for i in range(3)
		]
		
		# Test
		await self.processor._process_batch(tasks)
		
		# Verify
		assert self.mock_caption_generator.generate_caption_async.call_count == 3



	@pytest.mark.asyncio
	async def test_wait_for_queue_empty_already_empty(self):
		"""Test waiting for empty queue when already empty."""
		# Test
		result = await self.processor.wait_for_queue_empty(timeout=1.0)
		
		# Verify
		assert result is True

	@pytest.mark.asyncio
	async def test_wait_for_queue_empty_with_items(self):
		"""Test waiting for queue to become empty."""
		# Setup - add item to queue
		self.mock_index.get_name.return_value = ""
		self.processor.queue_caption_generation(
			uuid=self.test_uuid_1, int_id=1, block_content={}, block_type=self.TEST_BLOCK_TYPE
		)
		
		# Start processing to consume the queue
		await self.processor.start_background_processing()
		
		# Test
		result = await self.processor.wait_for_queue_empty(timeout=5.0)
		
		# Cleanup
		await self.processor.stop_background_processing()
		
		# Verify
		assert result is True

	@pytest.mark.asyncio
	async def test_caption_task_dataclass(self):
		"""Test CaptionTask dataclass functionality."""
		# Test task creation
		task = CaptionTask(
			uuid=self.test_uuid_1,
			int_id=1,
			block_content={"content": "test"},
			block_type=self.TEST_BLOCK_TYPE
		)
		assert task.uuid == self.test_uuid_1
		assert task.int_id == 1
		assert task.block_content == {"content": "test"}
		assert task.block_type == self.TEST_BLOCK_TYPE

	@pytest.mark.asyncio
	async def test_integration_full_workflow(self):
		"""Test full integration workflow with real processing."""
		# Setup
		self.mock_caption_generator.generate_caption_async = AsyncMock(return_value="Generated Caption")
		self.mock_index.get_name.return_value = ""
		self.mock_index.update_name_if_empty.return_value = True
		
		# Start processor
		await self.processor.start_background_processing()
		
		# Queue some tasks
		for i in range(3):
			self.processor.queue_caption_generation(
				uuid=self.test_uuid_1,
				int_id=i,
				block_content={"content": f"test{i}"},
				block_type=self.TEST_BLOCK_TYPE
			)
		
		# Wait for processing to complete
		await self.processor.wait_for_queue_empty(timeout=10.0)
		
		# Stop processor
		await self.processor.stop_background_processing()
		
		# Verify
		assert self.mock_caption_generator.generate_caption_async.call_count == 3


if __name__ == '__main__':
	pytest.main([__file__, "-v"]) 