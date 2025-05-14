# TODO: Move to common
import re

from tz_common.logs import log

class UrlIndex():
	
	# No persistent storage. TODO: Consider adding it?

	def __init__(self):
	
		self.index_to_url = {}
		self.url_to_index = {}


	def add_url(self, url: str):
		if url not in self.url_to_index:
			self.index_to_url[len(self.index_to_url)] = url
			self.url_to_index[url] = len(self.index_to_url)
			log.debug(f"Added url {url} to index {len(self.index_to_url)}")
		else:
			log.debug(f"URL {url} already exists in index")


	def get_url(self, index: int) -> str:
		url = self.index_to_url.get(index, None)
		if url is None:
			log.error(f"URL not found for index {index}")
		return url
	

	def get_index(self, url: str) -> int:
		index = self.url_to_index.get(url, None)
		if index is None:
			log.error(f"Index not found for URL {url}")
		return index


	def url_to_placeholder(self, url: str) -> str:
		return f"[[{self.url_to_index[url]}]]"


	def is_url(self, url: str) -> bool:
		# Using a simple regex pattern to check if the string is a URL
		pattern = re.compile(
			r'^(?:http|ftp)s?://'  # http:// or https://
			r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'  # domain...
			r'localhost|'  # localhost...
			r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}|'  # ...or ipv4
			r'\[?[A-F0-9]*:[A-F0-9:]+\]?)'  # ...or ipv6
			r'(?::\d+)?'  # optional port
			r'(?:/?|[/?]\S+)$', re.IGNORECASE)
		
		return re.match(pattern, url) is not None


	def replace_urls(self, input: dict) -> str:

		def search_and_replace(obj):
			if isinstance(obj, dict):
				for key, value in obj.items():
					if key == "url" and isinstance(value, str):
						obj[key] = self.url_to_placeholder(value)
					else:
						search_and_replace(value)
			elif isinstance(obj, list):
				for item in obj:
					search_and_replace(item)
			return obj

		return search_and_replace(input)
		

	def replace_placeholders(self, text: str) -> str:


		def replace_placeholder_with_url(match):
			try:
				index = int(match.group(1))
				log.debug(f"Replacing placeholder {index} with URL {self.get_url(index)}")
				return self.get_url(index)
			except ValueError:
				log.error(f"Invalid placeholder index: {match.group(1)}")
				return match.group(0)

		pattern = re.compile(r'\[\[(\d+)\]\]')
		return pattern.sub(replace_placeholder_with_url, text)
