import threading
import time
from abc import ABC, abstractmethod
from tz_common.logs import log

class TimedStorage(ABC):
	"""
	Class that schedules saving after a set period has passed since the last update.
	Useful when you don't know the conversation duration/frequency in advance.
	"""

	def __init__(self, period_ms: int = 5000, run_on_start: bool = True):

		self._periodic_save_lock = threading.RLock()
		self._stop_event = threading.Event()
		self._timer = threading.Thread(target=self._save_periodically, daemon=True)

		self.period_ms = period_ms
		self.dirty = False
		self.last_update = time.time()

		if run_on_start:
			self._timer.start()


	def set_dirty(self):
		try:
			# Add timeout to prevent indefinite blocking
			if self._periodic_save_lock.acquire(timeout=1.0):
				try:
					self.dirty = True
					self.last_update = time.time()
				finally:
					self._periodic_save_lock.release()
			else:
				# FIXME: This actully happens all the time :/
				log.error(f"{self.__class__.__name__}: Failed to acquire lock in set_dirty()")
		except Exception as e:
			log.error(f"{self.__class__.__name__}: Error in set_dirty(): {e}")


	def clean(self):

		with self._periodic_save_lock:
			self.dirty = False


	def is_dirty(self):
		with self._periodic_save_lock:
			return self.dirty


	def _save_periodically(self):

		while not self._stop_event.is_set():
			time.sleep(0.1)  # check periodically
			try:
				# Add timeout to prevent indefinite blocking
				if self._periodic_save_lock.acquire(timeout=1.0):
					try:
						if self.dirty and (time.time() - self.last_update) * 1000 >= self.period_ms:
							self.save()
							self.dirty = False
							log.flow(f"Saved {self.__class__.__name__}")
					finally:
						self._periodic_save_lock.release()
			except Exception as e:
				log.error(f"{self.__class__.__name__}: Error in _save_periodically(): {e}")


	@abstractmethod
	def save(self):
		"""
		Actually perform saving to storage, database etc.
		"""
		pass

	# TODO: Consider abstract load method that sets dirty to false


	def start_periodic_save(self):

		with self._periodic_save_lock:
			if not self._timer.is_alive():
				self.last_update = time.time()
				self._stop_event.clear()
				self._timer = threading.Thread(target=self._save_periodically, daemon=True)
				self._timer.start()


	def stop_periodic_save(self):

		self._stop_event.set()
		self._timer.join()

	
	def save_now(self):
		with self._periodic_save_lock:
			self.save()
			log.flow(f"Saved {self.__class__.__name__}")
		self.clean()
