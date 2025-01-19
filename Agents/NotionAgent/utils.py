from datetime import datetime, timezone

class Utils:

	@staticmethod
	def get_current_time_isoformat():
		return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

	@staticmethod
	def convert_date_to_timestamp(date: str) -> str:
		return datetime.strptime(date, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc).timestamp()