import asyncio
from typing import Optional, Dict, Any
from dataclasses import dataclass

from tz_common import CustomUUID
from tz_common.logs import log
from langfuse.callback import CallbackHandler

from .captionGenerator import CaptionGenerator
from ..blocks.blockHolder import BlockHolder
from ..blocks.index import Index


@dataclass
class CaptionTask:
	"""Represents a caption generation task in the queue."""
	uuid: CustomUUID
	int_id: int
	block_content: Dict[str, Any]
	block_type: str


class BackgroundCaptionProcessor:
	"""
	Manages background processing queue and async execution for caption generation.
	Processes caption generation tasks asynchronously without blocking main operations.
	"""

	def __init__(self, 
				 caption_generator: CaptionGenerator,
				 index: Index,
				 max_queue_size: int = 1000,
				 batch_size: int = 5,
				 max_concurrent: int = 8):
		"""
		Initialize the background caption processor.
		
		Args:
			caption_generator: CaptionGenerator instance for generating captions
			index: Index instance for updating block names
			max_queue_size: Maximum number of tasks in queue before dropping
			batch_size: Number of captions to process concurrently
			max_concurrent: Maximum concurrent caption generation tasks
		"""
		self.caption_generator = caption_generator
		self.index = index
		self.max_queue_size = max_queue_size
		self.batch_size = batch_size
		self.max_concurrent = max_concurrent
		
		# Queue and processing state
		self.task_queue: asyncio.Queue[CaptionTask] = asyncio.Queue(maxsize=max_queue_size)
		self.processing_task: Optional[asyncio.Task] = None
		self.is_running = False
		self.is_shutting_down = False


	def queue_caption_generation(self, 
								 uuid: CustomUUID, 
								 int_id: int, 
								 block_content: Dict[str, Any], 
								 block_type: str) -> bool:
		"""
		Queue a caption generation task for background processing.
		
		Args:
			uuid: UUID of the block
			int_id: Integer ID of the block
			block_content: Block content dictionary
			block_type: Type of the block (page, block, database)
			
		Returns:
			True if task was queued, False if queue is full or shutting down
		"""
		if self.is_shutting_down:
			log.debug(f"Skipping caption generation for {int_id}: processor is shutting down")
			return False
		
		# Check if block already has a name - skip if it does
		existing_name = self.index.get_name(int_id)
		if existing_name and existing_name.strip():
			log.debug(f"Skipping caption generation for {int_id}: already has name '{existing_name}'")
			return False
		
		# Create task
		task = CaptionTask(
			uuid=uuid,
			int_id=int_id,
			block_content=block_content,
			block_type=block_type
		)
		
		try:
			# Try to add to queue (non-blocking)
			self.task_queue.put_nowait(task)
			log.debug(f"Queued caption generation for {block_type} {int_id}")
			return True
			
		except asyncio.QueueFull:
			log.debug(f"Caption queue full, dropping task for {block_type} {int_id}")
			return False


	async def start_background_processing(self) -> None:
		"""Start the background processing worker."""
		if self.is_running:
			log.debug("Background caption processor already running")
			return
		
		self.is_running = True
		self.is_shutting_down = False
		
		# Start the background worker task
		self.processing_task = asyncio.create_task(self._process_caption_queue())
		log.flow("Started background caption processor")


	async def stop_background_processing(self, timeout: float = 30.0) -> None:
		"""
		Stop the background processing worker gracefully.
		
		Args:
			timeout: Maximum time to wait for graceful shutdown
		"""
		if not self.is_running:
			log.debug("Background caption processor not running")
			return
		
		log.flow("Stopping background caption processor...")
		self.is_shutting_down = True
		
		# Cancel the processing task
		if self.processing_task and not self.processing_task.done():
			self.processing_task.cancel()
			
			try:
				await asyncio.wait_for(self.processing_task, timeout=timeout)
			except asyncio.TimeoutError:
				log.error(f"Background caption processor did not stop within {timeout}s")
			except asyncio.CancelledError:
				log.debug("Background caption processor cancelled")
		
		self.is_running = False
		self.processing_task = None
		log.flow("Background caption processor stopped")


	async def _process_caption_queue(self) -> None:
		"""
		Main background worker that processes caption generation tasks.
		Runs continuously until shutdown is requested.
		"""
		log.debug("Background caption processor worker started")
		
		try:
			while not self.is_shutting_down:
				try:
					# Collect a batch of tasks
					batch = await self._collect_batch()
					
					if not batch:
						# No tasks available, wait a bit
						await asyncio.sleep(1.0)
						continue
					
					# Process the batch concurrently
					await self._process_batch(batch)
					
				except asyncio.CancelledError:
					log.debug("Caption processor worker cancelled")
					break
				except Exception as e:
					log.error(f"Error in caption processor worker: {e}")
					# Continue processing despite errors
					await asyncio.sleep(1.0)
		
		finally:
			log.debug("Background caption processor worker finished")


	async def _collect_batch(self) -> list[CaptionTask]:
		"""
		Collect a batch of tasks from the queue.
		
		Returns:
			List of tasks to process (up to batch_size)
		"""
		batch = []
		
		try:
			# Get first task (blocking with timeout)
			first_task = await asyncio.wait_for(self.task_queue.get(), timeout=5.0)
			batch.append(first_task)
			
			# Collect additional tasks (non-blocking)
			while len(batch) < self.batch_size:
				try:
					task = self.task_queue.get_nowait()
					batch.append(task)
				except asyncio.QueueEmpty:
					break
			
		except asyncio.TimeoutError:
			# No tasks available within timeout
			pass
		
		return batch


	async def _process_batch(self, batch: list[CaptionTask]) -> None:
		"""
		Process a batch of caption tasks concurrently.
		
		Args:
			batch: List of caption tasks to process
		"""
		if not batch:
			return
		
		log.debug(f"Processing caption batch of {len(batch)} tasks")
		
		# Create semaphore to limit concurrent operations
		semaphore = asyncio.Semaphore(self.max_concurrent)
		
		async def process_single_task(task: CaptionTask) -> None:
			"""Process a single caption task with semaphore control."""
			async with semaphore:
				await self._process_single_caption(task)
		
		# Process all tasks in the batch concurrently
		await asyncio.gather(
			*[process_single_task(task) for task in batch],
			return_exceptions=True
		)


	async def _process_single_caption(self, task: CaptionTask) -> None:
		"""
		Process a single caption generation task.
		
		Args:
			task: Caption task to process
		"""
		try:
			# Generate caption
			caption = await self.caption_generator.generate_caption_async(
				task.block_content, 
				task.block_type
			)
			
			if caption:
				# Update the index with the generated caption (only if empty)
				updated = self.index.update_name_if_empty(task.int_id, caption)
				if updated:
					log.debug(f"Generated and stored caption for {task.block_type} {task.int_id}: '{caption}'")
				else:
					log.debug(f"Skipped updating caption for {task.block_type} {task.int_id}: name already exists")
			else:
				log.debug(f"Caption generation failed for {task.block_type} {task.int_id}")
			
		except Exception as e:
			log.error(f"Error processing caption for {task.block_type} {task.int_id}: {e}")


	async def wait_for_queue_empty(self, timeout: float = 60.0) -> bool:
		"""
		Wait for the queue to become empty.
		
		Args:
			timeout: Maximum time to wait
			
		Returns:
			True if queue became empty, False if timeout
		"""
		start_time = asyncio.get_event_loop().time()
		
		while self.task_queue.qsize() > 0:
			if asyncio.get_event_loop().time() - start_time > timeout:
				return False
			await asyncio.sleep(0.1)
		
		return True 