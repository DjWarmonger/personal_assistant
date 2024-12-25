import re
import sqlite3
import threading
import time
from typing import List, Tuple

from tz_common.logs import log
from tz_common.timed_storage import TimedStorage

# TODO: Move uuid conversion to common class, share uuids between projects

class Index(TimedStorage):

	UUID_PATTERN = re.compile(r'^[0-9a-f]{8}-?[0-9a-f]{4}-?[0-9a-f]{4}-?[0-9a-f]{4}-?[0-9a-f]{12}$', re.IGNORECASE)

	def __init__(self):
		super().__init__(period_ms=3000, run_on_start=False)

		self.conn = sqlite3.connect(':memory:', check_same_thread=False)
		self.cursor = self.conn.cursor()
		self.lock = threading.Lock()
		self.load_from_disk()
		self.create_table()

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


	def validate_notion_id(self, notion_id):
		if not notion_id:
			return False
		
		return bool(self.UUID_PATTERN.match(notion_id))
	
	def clean_uuid(self, uuid: str) -> str:
		return uuid.replace("-", "")

	def add_uuid(self, uuid: str, name: str = "", item_type: str = "") -> int:
		uuid = self.clean_uuid(uuid)
		with self.lock:
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

			if self.validate_notion_id(id):
				return id
			else:
				raise ValueError("Invalid uuid")
		else:
			raise TypeError("Invalid type for conversion to uuid")
		
	def to_formatted_uuid(self, uuid: str) -> str:
		# Convert to 8-4-4-4-12 form

		clean = self.to_uuid(uuid)
		return f"{clean[:8]}-{clean[8:12]}-{clean[12:16]}-{clean[16:20]}-{clean[20:]}"

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
		self.save()
		self.conn.close()
