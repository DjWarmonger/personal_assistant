# async_manager.py
import asyncio
import time
import httpx
import atexit

class AsyncClientManager:
	_instance = None
	_request_lock = None
	_last_request_time = 0
	_period = 1000 // 3 # Notion API can be accessed at 3 requests per second
	_async_client = None
	_cleanup_registered = False

	def __new__(cls):
		"""Ensure we only have one instance."""
		if cls._instance is None:
			cls._instance = super().__new__(cls)
			if not cls._cleanup_registered:
				cls._register_cleanup()
				cls._cleanup_registered = True
		return cls._instance

	@classmethod
	def _register_cleanup(cls):
		def _cleanup():
			try:
				loop = asyncio.get_event_loop()
				if loop.is_running():
					loop.create_task(cls.cleanup())
				else:
					loop.run_until_complete(cls.cleanup())
			except:
				# If the event loop is already closed, create a new one.
				loop = asyncio.new_event_loop()
				asyncio.set_event_loop(loop)
				loop.run_until_complete(cls.cleanup())
				loop.close()

		atexit.register(_cleanup)

	@classmethod
	def reset(cls):
		"""Reset the manager state - useful when switching event loops."""
		cls._request_lock = None
		if cls._async_client is not None:
			# Note: this might need to be handled carefully if there are pending requests
			cls._async_client = None

	@classmethod
	async def initialize(cls):
		"""Initialize the shared HTTP client and lock if not already."""
		current_loop = asyncio.get_running_loop()
		
		# Reset if we detect a different event loop
		if cls._request_lock is not None and cls._request_lock._loop is not current_loop:
			cls.reset()
		
		if cls._async_client is None:
			cls._async_client = httpx.AsyncClient()
		if cls._request_lock is None:
			cls._request_lock = asyncio.Lock()

	@classmethod
	async def cleanup(cls):
		"""Close the shared HTTP client."""
		if cls._async_client is not None:
			await cls._async_client.aclose()
			cls._async_client = None

	@classmethod
	async def get_client(cls) -> httpx.AsyncClient:
		"""Return the shared client, ensuring it's initialized."""
		if cls._async_client is None:
			await cls.initialize()
		return cls._async_client

	@classmethod
	async def wait_for_next_request(cls):
		"""Perform rate-limiting according to _period."""
		await cls.initialize()  # This will handle event loop changes
		
		async with cls._request_lock:
			current_time = time.time() * 1000
			time_since_last_request = current_time - cls._last_request_time
			if time_since_last_request < cls._period:
				wait_time = (cls._period - time_since_last_request) / 1000
				await asyncio.sleep(wait_time)
			cls._last_request_time = time.time() * 1000
