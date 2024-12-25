import yaml

class YamlConverter:

	def json_to_yaml_string(self, json_data):
		yaml_data = self.json_to_yaml(json_data)
		string = str(yaml_data)
		string = string.replace("  ", '\t')
		return string
	
	def json_to_yaml(self, json_data):
		yaml_data = yaml.dump(json_data)
		return yaml_data

	def yaml_to_json(self, yaml_data):
		json_data = yaml.load(yaml_data)
		return json_data