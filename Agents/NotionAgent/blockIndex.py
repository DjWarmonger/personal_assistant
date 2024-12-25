import json
import sqlite3

from tz_common import log

class NotionItem:
	def __init__(self, name, notion_id, key):
		self.name = name
		self.notion_id = notion_id
		self.key = key
		


class NotionIndex:
	def __init__(self, db_path='notion_index.db'):
		self.db_path = db_path
		self.items = {}
		self._create_table()
		self._load_from_db()

	def __del__(self):
		self._save_to_db()

	def _create_table(self):
		with sqlite3.connect(self.db_path) as conn:
			cursor = conn.cursor()
			cursor.execute('''
				CREATE TABLE IF NOT EXISTS notion_items (
					key INTEGER PRIMARY KEY,
					name TEXT,
					notion_id TEXT
				)
			''')
			conn.commit()

	def _load_from_db(self):
		with sqlite3.connect(self.db_path) as conn:
			cursor = conn.cursor()
			cursor.execute('SELECT key, name, notion_id FROM notion_items')
			for key, name, notion_id in cursor.fetchall():
				self.items[key] = NotionItem(name, notion_id, key)

	def _save_to_db(self):
		with sqlite3.connect(self.db_path) as conn:
			cursor = conn.cursor()
			cursor.execute('DELETE FROM notion_items')
			for item in self.items.values():
				cursor.execute('''
					INSERT INTO notion_items (key, name, notion_id)
					VALUES (?, ?, ?)
				''', (item.key, item.name, item.notion_id))
			conn.commit()

	def create_item(self, name, notion_id, key):
		item = NotionItem(name, notion_id, key)
		self.items[key] = item

	def read_item(self, key):
		return self.items.get(key)
	
	def key_exists(self, key):
		return key in self.items

	def update_item(self, key, name=None, notion_id=None):
		item = self.items.get(key)
		if item:
			if name:
				item.name = name
			if notion_id:
				item.notion_id = notion_id

	def delete_item(self, key):
		if key in self.items:
			del self.items[key]
			
	def save_to_file(self, filename):
		with open(filename, 'w') as file:
			json_data = {key: item.__dict__ for key, item in self.items.items()}
			json.dump(json_data, file, indent=4)

	def load_from_file(self, filename):
		try:
			with open(filename, 'r') as file:
				json_data = json.load(file)
				self.items = {int(key): NotionItem(**item_data) for key, item_data in json_data.items()}
		except FileNotFoundError:
			log.flow(f"File {filename} not found. Starting with an empty index.")
		except json.JSONDecodeError:
			log.error(f"Error decoding JSON from {filename}. Starting with an empty index.")
			
	def key_to_notion_id(self, key):
		item = self.read_item(key)
		if item:
			return item.notion_id
		return None

	def notion_id_to_key(self, notion_id):
		for key, item in self.items.items():
			if item.notion_id == notion_id:
				return key
		return None

	def get_all_keys(self):
		return list(self.items.keys())

	def get_all_notion_ids(self):
		return [item.notion_id for item in self.items.values()]

	def get_all_names(self):
		return [item.name for item in self.items.values()]

# Example usage
index = NotionIndex()
index.create_item("Page 1", "notion_id_1", 1)
item = index.read_item(1)
index.update_item(1, name="Updated Page 1")
index.delete_item(1)
# The changes will be saved to the database when the NotionIndex object is destroyed
