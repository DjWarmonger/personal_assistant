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

		self._periodic_save_lock = threading.Lock()
		self._stop_event = threading.Event()
		self._timer = threading.Thread(target=self._save_periodically, daemon=True)

		self.period_ms = period_ms
		self.dirty = False
		self.last_update = time.time()

		if run_on_start:
			self._timer.start()


	def set_dirty(self, mode = True):

		with self._periodic_save_lock:
			self.dirty = mode
			self.last_update = time.time()


	def clean(self):

		with self._periodic_save_lock:
			self.dirty = False


	def is_dirty(self):
		return self.dirty


	def _save_periodically(self):

		while not self._stop_event.is_set():
			time.sleep(0.1)  # check periodically
			with self._periodic_save_lock:
				if self.dirty and (time.time() - self.last_update) * 1000 >= self.period_ms:
					self.save()
					self.dirty = False
					# TODO: Allow custom name in  logs?
					log.flow(f"Saved {self.__class__.__name__}")


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
