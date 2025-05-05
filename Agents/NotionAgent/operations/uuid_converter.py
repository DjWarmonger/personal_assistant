import re

class UUIDConverter:
	
	UUID_PATTERN = re.compile(r'^[0-9a-f]{8}-?[0-9a-f]{4}-?[0-9a-f]{4}-?[0-9a-f]{4}-?[0-9a-f]{12}$', re.IGNORECASE)


	def __init__(self):
		pass


	def clean_uuid(self, uuid: str) -> str:
		return uuid.replace("-", "").lower()


	def to_formatted_uuid(self, uuid: str) -> str:
		# Convert to 8-4-4-4-12 form
		clean = self.to_uuid(uuid)
		return f"{clean[:8]}-{clean[8:12]}-{clean[12:16]}-{clean[16:20]}-{clean[20:]}".lower()


	def validate_uuid(self, uuid: str) -> bool:
		if not uuid:
			return False
		
		if type(uuid) == int:
			return False
		
		return bool(self.UUID_PATTERN.match(uuid))


	def to_uuid(self, uuid: str) -> str:
		"""Convert any valid UUID format to clean 32-char format"""
		if not self.validate_uuid(uuid):
			raise ValueError("Invalid UUID format")
		return self.clean_uuid(uuid)
	

	def strip_cache_prefix(self, uuid: str) -> str:

		prefix, uuid = uuid.split(":")
		return self.to_uuid(uuid)

