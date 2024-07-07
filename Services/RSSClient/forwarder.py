import requests
from flask import Flask, jsonify, request
import os
from termcolor import colored

from rssDatabase import RSSDatabase

app = Flask(__name__)

class RSSForwarder:
	def __init__(self):
		self.db = RSSDatabase()
		self.generator = None

	def send_one(self, item, url):
		try:
			response = requests.post(url, json=item)
			if response.status_code == 200:
				print(f"Successfully forwarded item: {item['title']}")
				
				# TODO: Delete item from database
				# TODO: More advanced: Move it to trash and delete after some time
			else:
				print(colored(f"Failed to forward item: {item['title']}. Status code: {response.status_code}", 'red'))
		except requests.RequestException as e:
			print(colored(f"Error forwarding item: {item['title']}. Error: {str(e)}", 'red'))

	def send_next(self):
		url = os.getenv('POST_URL')

		if self.generator is None:
			self.generator = self.db.get_all_items()

		if self.generator:
			item = next(self.generator)
			self.send_one(item, url)
		else:
			self.generator = None
			return

	def forward_items(self, url = None):
		if url is None:
			url = os.getenv('POST_URL')
			
		items = self.db.get_all_items()
		for item in items:
			self.send_one(item, url)

@app.route('/forward', methods=['POST'])
def forward():
	data = request.json
	if 'url' not in data:
		return jsonify({'error': 'URL is required'}), 400

	forwarder = RSSForwarder()
	forwarder.forward_items(data['url'])
	return jsonify({'message': 'Forwarding completed'}), 200

if __name__ == '__main__':
	app.run(debug=True)
