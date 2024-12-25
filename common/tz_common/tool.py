import json

class Tool:

	class ToolParameter:
		def __init__(self, name: str, description: str, type: str):
			self.name = name
			self.type = type
			self.description = description

		def dict(self) -> dict[str, str]:
			return {
				"name": self.name,
				"type": self.type,
				"description": self.description
			}

	def __init__(self, name: str, description: str, parameters: list[ToolParameter]):
		self.name = name
		self.description = description
		self.parameters = parameters

	def dict(self) -> dict[str, dict[str, str]]:

		parameters = {}

		for param in self.parameters:
			d = param.dict()
			parameters[d["name"]] = {
				"type": d["type"],
				"description": d["description"]
			}

		return {
			"name": self.name,
			"description": self.description,
			"parameters": parameters
		}
	
	def add_parameter(self, parameter: ToolParameter):
		self.parameters.append(parameter)
	
	def json(self) -> str:
		return json.dumps(self.dict())
	
	def __str__(self) -> str:
		return self.json()
	
	def parameters_str(self) -> str:
		return ", ".join([f"{key}={value}" for key, value in self.parameters.items()])