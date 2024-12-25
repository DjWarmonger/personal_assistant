import json
import os

from tz_common import log

class Context:

	def __init__(self, path: str = "context.json", context: dict[str, str] | None = None):
		self.path = path
		self.context = context if context is not None else dict()

	def field_str(self, field: str) -> str:
		return str(self.context[field]) if field in self.context else "EMPTY"
	
	def append_to_field(self, field: str, value: str):
		if field not in self.context:
			self.context[field] = []
		self.context[field].append(value)

	def add_to_field(self, field: str, value: str):
		if field not in self.context:
			self.context[field] = set()
		self.context[field].add(value)

	def update_field(self, field: str, value: list[str]):
		if field not in self.context:
			self.context[field] = set()
		self.context[field].update(value)

	def extend_field(self, field: str, value: list[str]):
		if field not in self.context:
			self.context[field] = []
		self.context[field].extend(value)

	def discard_from_field(self, field: str, value: str):
		if field in self.context:
			self.context[field].discard(value)

	def __getitem__(self, key: str) -> str | None:
		return self.context[key] if key in self.context else None

	def __setitem__(self, key: str, value: str):
		self.context[key] = value

	def save(self, path: str = None):

		if not path:
			path = self.path

		# Convert any sets to lists before JSON serialization
		serializable_context = {}
		for key, value in self.context.items():
			if isinstance(value, set):
				serializable_context[key] = list(value)
			else:
				serializable_context[key] = value
		
		os.makedirs(os.path.dirname(path), exist_ok=True)
		with open(path, "w") as f:
			json.dump(serializable_context, f)

	def load(self, path: str = None) -> bool:

		if not path:
			path = self.path

		try:
			with open(path, "r") as f:
				loaded_context = json.load(f)
				# Convert lists back to sets for fields that should be sets
				for key, value in loaded_context.items():
					if isinstance(value, list):
						# Check if this field was originally created using add_to_field or update_field

						# FIXME: This only works if set is initialzed before loading
						if key in self.context and isinstance(self.context[key], set):
							loaded_context[key] = set(value)
				self.context = loaded_context
			return True
		except Exception as e:
			log.error(f"Failed to load context from {path}:", e)
			return False