import json
import re

class JsonConverter:

	def remove_spaces(self, json_data) -> str:
		# Handle BlockDict objects by converting them to regular dicts first
		if hasattr(json_data, 'to_dict') and callable(getattr(json_data, 'to_dict')):
			json_data = json_data.to_dict()
		
		# Convert to string properly using json.dumps if input is not already a string
		json_string = json.dumps(json_data) if not isinstance(json_data, str) else json_data

		# First preserve strings by replacing them with placeholders
		strings = []
		def save_string(match):
			strings.append(match.group(0))
			return f"__STRING_{len(strings)-1}__"
		
		# Save strings and replace with placeholders
		
		json_string = re.sub(r'"[^"\\]*(?:\\.[^"\\]*)*"', save_string, json_string)
		
		# Remove spaces between tokens
		json_string = re.sub(r'\s+', '', json_string)
		
		# Restore original strings
		for i, string in enumerate(strings):
			json_string = json_string.replace(f"__STRING_{i}__", string)
		
		return json_string
