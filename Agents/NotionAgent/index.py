import re
import sqlite3
import threading
from typing import List, Tuple
from urllib.parse import urlparse

from tz_common.logs import log
from tz_common.timed_storage import TimedStorage
from uuid_converter import UUIDConverter
"""
TODO: Split class responsibilities:
- Database management
- Notion-specific URL and block UUID handling
- Favourites management
"""

class Index(TimedStorage):

	def __init__(self, load_from_disk=True, run_on_start=False):
		super().__init__(period_ms=3000, run_on_start=run_on_start)

		self.converter = UUIDConverter()

		self.conn = sqlite3.connect(':memory:', check_same_thread=False)
		self.cursor = self.conn.cursor()
		self.lock = threading.Lock()

		if load_from_disk:
			self.load_from_disk()
		self.create_table()
		self.create_favourites_table()

		if (run_on_start):
			self.start_periodic_save()


	def create_table(self):
		table_exists = self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='index_data'").fetchone()
		if not table_exists:
			self.cursor.execute('''
				CREATE TABLE IF NOT EXISTS index_data (
					int_id INTEGER PRIMARY KEY AUTOINCREMENT,
					uuid TEXT UNIQUE,
					item_type TEXT,
					name TEXT,
					visit_count INTEGER DEFAULT 0
				)
			''')
			self.conn.commit()
			self.set_dirty()


	def create_favourites_table(self):
		table_exists = self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='favourites'").fetchone()
		if not table_exists:
			self.cursor.execute('''
				CREATE TABLE IF NOT EXISTS favourites (
					uuid TEXT UNIQUE
				)
			''')
			self.conn.commit()
			self.set_dirty()


	def get_favourites(self, count: int = 10) -> List[str]:
		with self.lock:
			self.cursor.execute('''
				SELECT f.uuid 
				FROM favourites f
				JOIN index_data i ON f.uuid = i.uuid
				ORDER BY i.visit_count DESC 
				LIMIT ?
			''', (count,))
			results = self.cursor.fetchall()

			# TODO: May want to return visit count and name as well?
			#log.debug(f"Favourites:", results)
			return [result[0] for result in results]
	
	def set_favourite(self, uuid: str | list[str], add: bool) -> str:

		message = ""

		if isinstance(uuid, str):
			uuid = self.converter.clean_uuid(uuid)
		elif isinstance(uuid, list):
			uuid = [self.converter.clean_uuid(u) for u in uuid]
		else:
			raise ValueError(f"Invalid type for set_favourite : {type(uuid)}")

		with self.lock:
			if isinstance(uuid, str):
				if add:
					self.cursor.execute('INSERT OR REPLACE INTO favourites (uuid) VALUES (?)', (uuid,))
				else:
					self.cursor.execute('DELETE FROM favourites WHERE uuid = ?', (uuid,))

				message = f"{'Added to' if add else 'Removed from'} favourites : {uuid}"

			elif isinstance(uuid, list):
				if add:
					self.cursor.executemany('INSERT OR REPLACE INTO favourites (uuid) VALUES (?)', [(u,) for u in uuid])
				else:
					self.cursor.executemany('DELETE FROM favourites WHERE uuid = ?', [(u,) for u in uuid])

				message = f"{'Added to' if add else 'Removed from'} favourites : {', '.join(uuid)}"

			self.conn.commit()
			self.set_dirty()

		log.debug(message)
		return message
	

	def set_favourite_int(self, id : int | list[int], add: bool) -> str:

		with self.lock:
			if isinstance(id, int):
				uuids = self.get_uuid(id)
			elif isinstance(id, list):
				uuids = [self.get_uuid(i) for i in id]
		# Remove None values from the list of UUIDs
		uuids = [uuid for uuid in uuids if uuid is not None]
		if not uuids:
			return "None of the provided ids were found in the index"

		return self.set_favourite(uuids, add)


	def validate_notion_url(self, notion_url) -> bool:
		if not notion_url:
			return False
		
		# TODO: Try to actually GET this url?
		parsed_url = urlparse(notion_url)
		return parsed_url.netloc == "www.notion.so"


	def url_to_uuid(self, url: str) -> str:
		# Extract UUID from URL using regex
		match = re.search(r'[0-9a-f]{32}', url.lower())
		if not match:
			raise ValueError("No UUID found in URL")
		
		uuid = match.group(0)
		if not self.converter.validate_uuid(uuid):
			raise ValueError("Invalid UUID format")
		
		return self.converter.clean_uuid(uuid)


	def add_uuid(self, uuid: str, name: str = "", item_type: str = "") -> int:
		uuid = self.converter.clean_uuid(uuid)
		with self.lock:
			self.cursor.execute('SELECT int_id FROM index_data WHERE uuid = ?', (uuid,))
			existing_id = self.cursor.fetchone()
			if existing_id:
				return existing_id[0]

			self.cursor.execute('''
				INSERT OR IGNORE INTO index_data (uuid, name, item_type)
				VALUES (?, ?, ?)
			''', (uuid, name, item_type))
			if self.cursor.rowcount > 0:
				self.set_dirty()
			self.conn.commit()

			return self.cursor.lastrowid

	def visit_uuid(self, uuid: str):
		with self.lock:
			self.cursor.execute('''
				UPDATE index_data
				SET visit_count = visit_count + 1
				WHERE uuid = ?
			''', (uuid,))
			self.conn.commit()
			self.set_dirty()

	def visit_int(self, int_id: int):
		with self.lock:
			self.cursor.execute('''
				UPDATE index_data
				SET visit_count = visit_count + 1
				WHERE int_id = ?
			''', (int_id,))
			self.conn.commit()
			self.set_dirty()

	def to_uuid(self, id: int | str) -> str:
		if isinstance(id, int):
			return self.get_uuid(id)
		elif isinstance(id, str):
			try:
				# Directly convert string to int
				int_id = int(id)
				return self.get_uuid(int_id)
			except ValueError:
				pass

			if self.converter.validate_uuid(id):
				return id
			else:
				raise ValueError("Invalid uuid")
		else:
			raise TypeError("Invalid type for conversion to uuid")
		

	
	def add_notion_url_or_uuid_to_index(self, url_or_uuid: str, title: str = "") -> int:

		if self.validate_notion_url(url_or_uuid):
			uuid = self.url_to_uuid(url_or_uuid)
		else:
			uuid = url_or_uuid

		if not self.converter.validate_uuid(uuid):
			raise ValueError(f"Invalid Notion UUID: {uuid}")

		# TODO: Determine item type from url?

		return self.add_uuid(uuid, name=title, item_type="page")


	def add_notion_url_or_uuid_to_favourites(self, url_or_uuid: str, set = True,title: str = "") -> int:

		notion_id = self.add_notion_url_or_uuid_to_index(url_or_uuid, title=title)
		self.set_favourite(url_or_uuid, set)
		return notion_id


	def to_int(self, uuid: str) -> int:
		with self.lock:
			self.cursor.execute('SELECT int_id FROM index_data WHERE uuid = ?', (uuid,))
			result = self.cursor.fetchone()
			return result[0] if result else None


	def get_uuid(self, int_id: int) -> str:
		with self.lock:
			self.cursor.execute('SELECT uuid FROM index_data WHERE int_id = ?', (int_id,))
			result = self.cursor.fetchone()
			return result[0] if result else None


	def get_int(self, uuid: str) -> int:
		# FIXME: This is just duplicated method from to_int
		return self.to_int(uuid)


	def get_visit_count(self, int_id: int) -> int:
		with self.lock:
			self.cursor.execute('SELECT visit_count FROM index_data WHERE int_id = ?', (int_id,))
			result = self.cursor.fetchone()
			return result[0] if result else 0


	def set_name(self, int_id: int, name: str):
		with self.lock:
			self.cursor.execute('UPDATE index_data SET name = ? WHERE int_id = ?', (name, int_id))
			self.conn.commit()
			self.set_dirty()


	def get_name(self, int_id: int) -> str:
		with self.lock:
			self.cursor.execute('SELECT name FROM index_data WHERE int_id = ?', (int_id,))
			result = self.cursor.fetchone()
			return result[0] if result else ""


	def delete_uuid(self, uuid: str) -> int:
		with self.lock:
			self.cursor.execute('DELETE FROM index_data WHERE uuid = ?', (uuid,))
			self.conn.commit()
			self.set_dirty()
			return self.cursor.rowcount


	def get_most_popular(self, count: int) -> str:
		with self.lock:
			self.cursor.execute('''
				SELECT int_id, name, item_type, visit_count
				FROM index_data
				ORDER BY visit_count DESC
				LIMIT ?
			''', (count,))
			results = self.cursor.fetchall()

		ret = "Index of most visited pages:\n"
		for int_id, name, item_type, visit_count in results:
			ret += f"{int_id}: {name} ({item_type}) - visits: {visit_count}\n"
		return ret


	def save(self):
		# Overrides abstract method
	
		with self.lock:
			disk_conn = sqlite3.connect('index.db')
			with disk_conn:
				self.conn.backup(disk_conn)
			log.flow("Index saved to disk")


	def load_from_disk(self):
		try:
			with self.lock:
				disk_conn = sqlite3.connect('index.db')
				disk_conn.backup(self.conn)
				log.flow("Index loaded from disk")
				self.set_dirty(False)
		except sqlite3.Error:
			log.flow("No existing index file found. Starting with an empty index.")


	def __del__(self):
		# FIXME: Do not do that during unit tests
		#self.save()
		self.conn.close()
