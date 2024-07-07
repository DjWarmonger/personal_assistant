import sqlite3
import datetime
from feedItem import FeedItem
import threading

class RSSDatabase:
	def __init__(self, db_name='rss_items.db'):
		self.db_name = db_name
		self.lock = threading.Lock()
		self.create_table()

	def _get_connection(self):
		return sqlite3.connect(self.db_name)

	def create_table(self):
		with self.lock:
			conn = self._get_connection()
			cursor = conn.cursor()
			cursor.execute('''
				CREATE TABLE IF NOT EXISTS feed_items (
					item_key TEXT PRIMARY KEY,
					title TEXT,
					link TEXT,
					summary TEXT,
					timestamp TEXT
				)
			''')
			conn.commit()
			conn.close()

	def add_item(self, feed_item: FeedItem):
		with self.lock:
			conn = self._get_connection()
			cursor = conn.cursor()
			cursor.execute('SELECT timestamp FROM feed_items WHERE item_key = ?', (feed_item.item_key,))
			existing_timestamp = cursor.fetchone()
			
			if existing_timestamp:
				timestamp = existing_timestamp[0]
			else:
				timestamp = feed_item.timestamp.isoformat()

			cursor.execute('''
				INSERT OR REPLACE INTO feed_items (item_key, title, link, summary, timestamp)
				VALUES (?, ?, ?, ?, ?)
			''', (feed_item.item_key, feed_item.title, feed_item.link, feed_item.summary, timestamp))
			conn.commit()
			conn.close()

	def get_item(self, item_key):
		with self.lock:
			conn = self._get_connection()
			cursor = conn.cursor()
			cursor.execute('SELECT title, link, summary, timestamp FROM feed_items WHERE item_key = ?', (item_key,))
			result = cursor.fetchone()
			conn.close()
			return FeedItem(item_key=item_key, title=result[0], link=result[1], summary=result[2], timestamp=datetime.datetime.fromisoformat(result[3])) if result else None
		
	def get_all_items(self):
		with self.lock:
			conn = self._get_connection()
			cursor = conn.cursor()
			cursor.execute('SELECT item_key, title, link, summary, timestamp FROM feed_items')
			for item in cursor:
				yield {
					'item_key': item[0],
					'title': item[1],
					'link': item[2],
					'summary': item[3],
					'timestamp': item[4]
				}
			conn.close()

	def item_exists(self, item_key):
		with self.lock:
			conn = self._get_connection()
			cursor = conn.cursor()
			cursor.execute('SELECT 1 FROM feed_items WHERE item_key = ?', (item_key,))
			result = cursor.fetchone() is not None
			conn.close()
			return result

	def close(self):
		pass  # No need to close a persistent connection

