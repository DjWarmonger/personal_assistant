import threading
import time
import os
from dotenv import load_dotenv

from rssClient import RSSClient
from forwarder import RSSForwarder


def main():
	# Load environment variables
	load_dotenv()

	client = RSSClient()

	# Fetch and display feed content periodically in a thread
	def periodic_fetch(client, interval=int(os.getenv("POLL_INTERVAL", 3600))):
		while True:
			client.fetch_feeds()
			time.sleep(interval)

	fetch_thread = threading.Thread(target=periodic_fetch, args=(client,))
	fetch_thread.daemon = True
	fetch_thread.start()
	
	# Initialize and start the RSSForwarder
	forwarder = RSSForwarder()
	
	def periodic_forward(forwarder, interval=int(os.getenv("SEND_INTERVAL", 1))):
		while True:
			forwarder.send_next()
			time.sleep(interval)
	
	forward_thread = threading.Thread(target=periodic_forward, args=(forwarder,))
	forward_thread.daemon = True
	forward_thread.start()

	# Keep the main thread alive
	try:
		while True:
			time.sleep(1)
	except KeyboardInterrupt:
		print("Exiting...")

if __name__ == "__main__":
	main()
