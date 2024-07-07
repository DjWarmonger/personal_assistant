from rssClient import RSSClient

client = RSSClient()
#client.add_feed("https://www.youtube.com/feeds/videos.xml?channel_id=UC_x36zCEGilGpB1m-V4gmjg")
client.print_feeds()

assert client.feeds == ["https://www.youtube.com/feeds/videos.xml?channel_id=UC_x36zCEGilGpB1m-V4gmjg"]

client.fetch_feeds()
#client.fetch_feeds()