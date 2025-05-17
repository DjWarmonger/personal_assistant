import re
import sqlite3
import threading
from typing import List, Tuple, Union, Dict, Optional
from urllib.parse import urlparse

from tz_common.logs import log
from tz_common.timed_storage import TimedStorage
from tz_common import CustomUUID
"""
TODO: Split class responsibilities:
- Database management
- Database locking and exception handling
- Notion-specific URL and block UUID handling
- Favourites management
"""

class Index(TimedStorage):

	# TODO: Separate test for loading from disk and running on start

	def __init__(self,
			  db_path: str = 'index.db',
			  load_from_disk: bool = False,
			  run_on_start: bool = False):

		self._is_closing = False
		self.save_enabled = run_on_start
		self.db_path = db_path

		super().__init__(period_ms=3000, run_on_start=run_on_start)

		self.db_conn = sqlite3.connect(':memory:', check_same_thread=False)
		self.cursor = self.db_conn.cursor()
		self.db_lock = threading.RLock()

		import atexit
		atexit.register(self.cleanup)

		if load_from_disk:
			self.load_from_disk()
			# Check if tables exist after loading
			if not self._tables_exist():
				self._create_tables()
		else:
			# Only create tables if we're not loading from disk
			self._create_tables()

		if (run_on_start):
			self.start_periodic_save()


	def _tables_exist(self):
		"""Check if required tables already exist"""
		try:
			self.cursor.execute("""
				SELECT name FROM sqlite_master 
				WHERE type='table' AND name='index_data'
			""")
			return self.cursor.fetchone() is not None
		except Exception as e:
			log.error(f"Error checking tables: {e}")
			return False


	def _create_tables(self):
		"""Create tables only if they don't exist"""
		try:
			with self.db_lock:
				# Use CREATE TABLE IF NOT EXISTS
				self.cursor.execute('''
					CREATE TABLE IF NOT EXISTS index_data (
						int_id INTEGER PRIMARY KEY AUTOINCREMENT,
						uuid TEXT UNIQUE,
						name TEXT,
						visit_count INTEGER DEFAULT 0
					)
				''')
				self.db_conn.commit()
				self.set_dirty()
				log.flow("Created index table")

			self.create_favourites_table()
		except Exception as e:
			log.error(f"Error creating tables: {e}")


	def create_favourites_table(self):
		with self.db_lock:
			table_exists = self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='favourites'").fetchone()
			if not table_exists:
				self.cursor.execute('''
					CREATE TABLE IF NOT EXISTS favourites (
						uuid TEXT UNIQUE
					)
				''')
				self.db_conn.commit()
				self.set_dirty()
				log.flow("Created favourites table")


	def get_favourites(self, count: int = 10) -> List[CustomUUID]:
		with self.db_lock:
			self.cursor.execute('''
				SELECT f.uuid 
				FROM favourites f
				JOIN index_data i ON f.uuid = i.uuid
				ORDER BY i.visit_count DESC 
				LIMIT ?
			''', (count,))
			results = self.cursor.fetchall()

			ret = [CustomUUID(value=result[0]) for result in results]
			log.common(f"Favourites:", [str(uuid) for uuid in ret])
			return ret
		

	def get_favourites_with_names(self, count: int = 10) -> List[Tuple[int, str]]:
		# TODO: Display visit count?

		with self.db_lock:
			self.cursor.execute('''
				SELECT i.int_id, i.name
				FROM favourites f
				JOIN index_data i ON f.uuid = i.uuid
				ORDER BY i.visit_count DESC 
				LIMIT ?
			''', (count,))
			results = self.cursor.fetchall()
			log.common("Favourites with descriptions:\n", "\n".join([f"{r[0]:02}: {r[1]}" for r in results]))
			return results


	def set_favourite(self, uuid: Union[CustomUUID, List[CustomUUID]], add: bool) -> str:
		message = ""

		with self.db_lock:
			if isinstance(uuid, CustomUUID):
				uuid_str = str(uuid)
				if add:
					self.cursor.execute('INSERT OR REPLACE INTO favourites (uuid) VALUES (?)', (uuid_str,))
				else:
					self.cursor.execute('DELETE FROM favourites WHERE uuid = ?', (uuid_str,))

				message = f"{'Added to' if add else 'Removed from'} favourites : {uuid_str}"

			elif isinstance(uuid, list):
				uuid_strs = [str(u) for u in uuid]
				if add:
					self.cursor.executemany('INSERT OR REPLACE INTO favourites (uuid) VALUES (?)', [(u,) for u in uuid_strs])
				else:
					self.cursor.executemany('DELETE FROM favourites WHERE uuid = ?', [(u,) for u in uuid_strs])

				message = f"{'Added to' if add else 'Removed from'} favourites : {', '.join(uuid_strs)}"
			else:
				raise ValueError(f"Invalid type for set_favourite: {type(uuid)}")

			self.db_conn.commit()
			self.set_dirty()

		log.debug(message)
		return message
	

	def set_favourite_int(self, id: Union[int, List[int]], add: bool) -> str:
		with self.db_lock:
			if isinstance(id, int):
				uuids = self.get_uuid(id)
				if uuids is None: # Handle case where single id doesn't return a UUID
					uuids = []
				else:
					uuids = [uuids]
			elif isinstance(id, list):
				uuids = [self.get_uuid(i) for i in id]
			else:
				raise ValueError(f"Invalid type for set_favourite_int: {type(id)}")
				
		# Remove None values from the list of UUIDs
		uuids = [uuid_obj for uuid_obj in uuids if uuid_obj is not None]
		if not uuids:
			return "None of the provided ids were found in the index"

		return self.set_favourite(uuids, add)


	def validate_notion_url(self, notion_url: str) -> bool:
		if not notion_url:
			return False
		
		# TODO: Try to actually GET this url?
		parsed_url = urlparse(notion_url)
		return parsed_url.netloc == "www.notion.so"


	def url_to_uuid(self, url: str) -> CustomUUID:
		# Extract UUID from URL using regex
		match = re.search(r'[0-9a-f]{32}', url.lower())
		if not match:
			raise ValueError("No UUID found in URL")
		
		uuid_str = match.group(0)
		try:
			return CustomUUID(value=uuid_str)
		except ValueError:
			raise ValueError("Invalid UUID format")


	def add_uuid(self, uuid: CustomUUID, name: str = "") -> int:
		uuid_str = str(uuid)

		# First check if UUID exists
		if not self.db_lock.acquire(timeout=5):  # 5 second timeout
			raise TimeoutError("Could not acquire lock for UUID check")
		
		try:
			self.cursor.execute("PRAGMA busy_timeout = 5000")
			self.cursor.execute('SELECT int_id FROM index_data WHERE uuid = ?', (uuid_str,))
			existing_id = self.cursor.fetchone()
			if existing_id:
				#log.debug(f"Returning existing UUID {uuid_str} from index")
				return existing_id[0]
		except sqlite3.OperationalError as e:
			log.error(f"Database error during UUID check: {e}")
			raise
		except Exception as e:
			log.error(f"Unexpected error during UUID check: {e}")
			raise
		finally:
			self.db_lock.release()
		
		# If not exists, add it with a new lock acquisition
		if not self.db_lock.acquire(timeout=5):
			log.error("Timeout while acquiring lock for UUID insertion")
			raise TimeoutError("Could not acquire lock for UUID insertion")
		
		try:
			self.cursor.execute("PRAGMA busy_timeout = 5000")
			self.cursor.execute('''
				INSERT OR IGNORE INTO index_data (uuid, name)
				VALUES (?, ?)
				''', (uuid_str, name))
			self.db_conn.commit()
			last_row_id = self.cursor.lastrowid

			if self.cursor.rowcount > 0:
				self.set_dirty()
			else:
				log.debug(f"UUID {uuid_str} already exists in index")
			
			return last_row_id
		except sqlite3.OperationalError as e:
			log.error(f"Database error during UUID insertion: {e}")
			raise
		except Exception as e:
			log.error(f"Unexpected error during UUID insertion: {e}")
			raise
		finally:
			self.db_lock.release()


	def visit_uuid(self, uuid: CustomUUID):
		"""
		Increase visit count for a page
		"""
		uuid_str = str(uuid)
		with self.db_lock:
			self.cursor.execute('''
				UPDATE index_data
				SET visit_count = visit_count + 1
				WHERE uuid = ?
			''', (uuid_str,))
			self.db_conn.commit()
			self.set_dirty()


	def visit_int(self, int_id: int):
		"""
		Increase visit count for a page
		"""
		with self.db_lock:
			self.cursor.execute('''
				UPDATE index_data
				SET visit_count = visit_count + 1
				WHERE int_id = ?
			''', (int_id,))
			self.db_conn.commit()
			self.set_dirty()


	def to_uuid(self, id_val: Union[int, str, CustomUUID]) -> Optional[CustomUUID]:
		if isinstance(id_val, int):
			return self.get_uuid(id_val)
		elif isinstance(id_val, str):
			try:
				# Try to convert string to int first, if it's a numerical string representation of an int_id
				int_id = int(id_val)
				return self.get_uuid(int_id)
			except ValueError:
				# If not an int, assume it's a UUID string
				try:
					return CustomUUID(value=id_val)
				except ValueError:
					log.error(f"Invalid uuid string: {id_val}")
					# Or, depending on desired behavior, return None or raise the ValueError
					# For now, let's return None for invalid UUID strings to avoid crashing
					return None 
		elif isinstance(id_val, CustomUUID):
			return id_val
		else:
			raise TypeError(f"Invalid type for conversion to uuid: {type(id_val)}")


	def add_notion_url_or_uuid_to_index(self, url_or_uuid: str, title: str = "") -> int:
		if self.validate_notion_url(url_or_uuid):
			uuid_obj = self.url_to_uuid(url_or_uuid)
		else:
			try:
				uuid_obj = CustomUUID(value=url_or_uuid)
			except ValueError:
				raise ValueError(f"Invalid Notion UUID string: {url_or_uuid}")

		# TODO: Determine item type from url?
		return self.add_uuid(uuid_obj, name=title)


	def add_notion_url_or_uuid_to_favourites(self, url_or_uuid: str, set_fav: bool = True, title: str = "") -> int:
		notion_id = self.add_notion_url_or_uuid_to_index(url_or_uuid, title=title)
		uuid_obj = self.get_uuid(notion_id)
		if uuid_obj:
			self.set_favourite(uuid_obj, set_fav)
		return notion_id


	def to_int(self, uuid: Union[CustomUUID, List[CustomUUID]]) -> Union[Optional[int], Dict[CustomUUID, Optional[int]]]:
		with self.db_lock:
			if isinstance(uuid, CustomUUID):
				uuid_str = str(uuid)
				self.cursor.execute('SELECT int_id FROM index_data WHERE uuid = ?', (uuid_str,))
				result = self.cursor.fetchone()
				return result[0] if result else None
			elif isinstance(uuid, list):
				uuid_strs = [str(u) for u in uuid]
				placeholders = ','.join('?' for _ in uuid_strs)
				query = f"SELECT uuid, int_id FROM index_data WHERE uuid IN ({placeholders})"
				self.cursor.execute(query, uuid_strs)
				rows = self.cursor.fetchall()
				return {CustomUUID(value=row[0]): row[1] for row in rows}
			else:
				raise ValueError(f"Invalid type for to_int: {type(uuid)}")


	def get_uuid(self, int_id: int) -> Optional[CustomUUID]:
		with self.db_lock:
			self.cursor.execute('SELECT uuid FROM index_data WHERE int_id = ?', (int_id,))
			result = self.cursor.fetchone()
			return CustomUUID(value=result[0]) if result else None


	def get_visit_count(self, int_id: int) -> int:
		with self.db_lock:
			self.cursor.execute('SELECT visit_count FROM index_data WHERE int_id = ?', (int_id,))
			result = self.cursor.fetchone()
			return result[0] if result else 0


	def set_name(self, int_id: int, name: str):
		with self.db_lock:
			self.cursor.execute('UPDATE index_data SET name = ? WHERE int_id = ?', (name, int_id))
			self.db_conn.commit()
			self.set_dirty()


	def get_name(self, int_id: int) -> str:
		with self.db_lock:
			self.cursor.execute('SELECT name FROM index_data WHERE int_id = ?', (int_id,))
			result = self.cursor.fetchone()
			return result[0] if result else ""


	def get_names(self, int_ids: List[int]) -> Dict[int, str]:
		with self.db_lock:
			placeholders = ','.join('?' for _ in int_ids)
			query = f"SELECT int_id, name FROM index_data WHERE int_id IN ({placeholders})"
			self.cursor.execute(query, int_ids)
			results = {row[0]: row[1] for row in self.cursor.fetchall()}
			return {id: results.get(id, "") for id in int_ids}


	def delete_uuid(self, uuid: CustomUUID) -> int:
		uuid_str = str(uuid)
		with self.db_lock:
			self.cursor.execute('DELETE FROM index_data WHERE uuid = ?', (uuid_str,))
			self.db_conn.commit()
			self.set_dirty()
			return self.cursor.rowcount


	def get_most_popular(self, count: int) -> str:
		with self.db_lock:
			self.cursor.execute('''
				SELECT int_id, name, visit_count
				FROM index_data
				ORDER BY visit_count DESC
				LIMIT ?
			''', (count,))
			results = self.cursor.fetchall()

		ret = "Index of most visited pages:\n"
		for int_id, name, visit_count in results:
			ret += f"{int_id}: {name} - visits: {visit_count}\n"
		return ret


	def load_from_disk(self):
		try:
			with self.db_lock:
				disk_conn = sqlite3.connect(self.db_path)
				disk_conn.backup(self.db_conn)
				disk_conn.close()
			log.flow("Index loaded from disk")
			self.clean()
		except sqlite3.Error:
			log.flow("No existing index file found. Starting with an empty index.")


	def save(self):
		#override
		if self._is_closing or not self.db_conn:
			return
		
		try:
			with self.db_lock:
				disk_conn = sqlite3.connect(self.db_path)
				self.db_conn.backup(disk_conn)
				disk_conn.close()
			log.flow("Index saved to disk")
		except Exception as e:
			log.error(f"Failed to save index to disk: {e}")


	def cleanup(self):
		#override
		# Don't do that during unit tests
		if not self.save_enabled:
			return

		if not self._is_closing and self.db_conn:
			try:
				self._is_closing = True
				self.save()  # Call the virtual save method
				self.db_conn.close()
			except Exception as e:
				log.error(f"Cleanup failed: {e}")
