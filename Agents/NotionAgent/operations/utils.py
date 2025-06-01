from datetime import datetime, timezone
from tz_common import CustomUUID

class Utils:

	@staticmethod
	def get_current_time_isoformat():
		return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


	@staticmethod
	def convert_date_to_timestamp(date: str) -> str:
		return datetime.strptime(date, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc).timestamp()


	@staticmethod
	def extract_notion_id(url):
		if url is None:
			return None
		
		base_url = "https://www.notion.so/"
		# TODO: Strip extra content, if any
		# TODO: Strip query parameters, if any
		formatted_id = url.replace(base_url, "")
		
		return formatted_id