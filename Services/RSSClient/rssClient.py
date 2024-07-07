import feedparser
import hashlib
from termcolor import colored
from datetime import datetime

from feedItem import FeedItem
from rssDatabase import RSSDatabase

class RSSClient:
	def __init__(self):
		self.feeds = []
		self.load_feeds_from_file()
		self.db = RSSDatabase()
	
	def add_feed(self, url):
		self.feeds.append(url)

	def add_item(self, item: FeedItem):
		self.db.add_item(item)

	def is_hash_new(self, item_hash):
		return not self.db.item_exists(item_hash)
		
	def load_feeds_from_file(self, filename = "feeds.txt"):
		self.feeds = []
		try:
			with open(filename, 'r') as file:
				for line in file:
					url = line.strip()
					if url:
						self.add_feed(url)
			print(colored(f"{len(self.feeds)} feeds loaded successfully from {filename}", "green"))
		except FileNotFoundError:
			print(colored(f"Error: File '{filename}' not found.", "red"))
		except IOError:
			print(colored(f"Error: Unable to read file '{filename}'.", "red"))
			
	def print_feeds(self):
		print(self.feeds)

	def fetch_feeds(self):

		# TODO: How to not read same feeds over and over?

		for feed_url in self.feeds:
			try:
				feed = feedparser.parse(feed_url)

				print(colored(f"\nFeed: {feed.feed.title}", "cyan"))
				print(f"fetched {len(feed.entries)} entries")
				for entry in feed.entries[:5]:  # Display the 5 most recent entries
					print(colored(f"Title: {entry.title}", "yellow"))
					print(f"Link: {entry.link}")
					print(f"Published: {entry.published}")
					print(f"Summary: {entry.summary[:100]}...")  # Display first 100 characters of summary
					print("-" * 50)

			except Exception as e:
				print(colored(f"Error fetching feed {feed_url}: {str(e)}", "red"))

			try:
				for entry in feed.entries:
					item_hash = self._generate_item_hash(entry)
					if self.is_hash_new(item_hash):
						published_time = entry.get('published_parsed')
						timestamp = datetime(*published_time[:6]) if published_time else None
						feed_item = FeedItem(
							item_key=item_hash,
							title=entry.title,
							link=entry.link,
							summary=entry.summary,
							timestamp=timestamp
						)
						self.add_item(feed_item)
					else:
						print(colored(f"Item already processed:", "red"), entry.title)
			except Exception as e:
				print(colored(f"Error processing feed {feed_url}: {str(e)}", "red"))


	def _generate_item_hash(self, item):
		content = f"{item.title}{item.link}"
		return hashlib.md5(content.encode('utf-8')).hexdigest()

	def __del__(self):
		self.db.close()

