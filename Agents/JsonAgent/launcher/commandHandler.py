import json
from pathlib import Path
from typing import Dict, Callable, Any, Optional, Union
from tz_common.logs import log

# TODO: Move to common?

class CommandHandler:
	"""
	Base class for handling chat commands in agent interfaces.
	Can be extended for different agents with specific commands.
	"""
	
	def __init__(self):
		self.commands: Dict[str, Callable] = {}
		self.command_aliases: Dict[str, str] = {}
		self.help_text = ""
		self._register_base_commands()
		
	def _register_base_commands(self):
		"""Register the basic commands available in all agents"""
		self.register_command("help", self._cmd_help, aliases=["?"])
		self.register_command("quit", self._cmd_quit)
	
	def register_command(self, name: str, handler: Callable, aliases: list = None):
		"""Register a new command with optional aliases"""
		name = name.lower()
		self.commands[name] = handler
		
		if aliases:
			for alias in aliases:
				self.command_aliases[alias.lower()] = name
	
	def set_help_text(self, help_text: str):
		"""Set the help text to be displayed when help command is called"""
		self.help_text = help_text
	
	def _cmd_help(self, *args, **kwargs):
		"""Default help command implementation"""
		if self.help_text:
			log.common(self.help_text)
		else:
			log.flow("No help text available. Use register_command() to add commands.")
		return True
	
	def _cmd_quit(self, *args, **kwargs):
		"""Default quit command implementation"""
		return "quit"
	
	def handle_command(self, user_input: str, args, current_state={}, **kwargs) -> Union[bool, str, dict]:
		"""
		Process a user command if it matches registered commands
		
		Args:
			user_input: The user's input text
			current_state: The current agent state dictionary (defaults to empty dict)
			**kwargs: Additional context passed to command handlers
			
		Returns:
			- True if command was handled
			- "quit" if application should exit
			- dict with updated state if state was modified
			- False if input wasn't a command
		"""
		if not user_input:
			return False
			
		user_input = user_input.lower().strip()
		
		# Check if it's a registered command
		if user_input in self.commands:
			return self.commands[user_input](args=args, current_state=current_state, **kwargs)
		
		# Check for aliases
		if user_input in self.command_aliases:
			command_name = self.command_aliases[user_input]
			return self.commands[command_name](args=args, current_state=current_state, **kwargs)
			
		return False


class JsonAgentCommandHandler(CommandHandler):
	"""Command handler specific to the JSON Agent"""
	
	def __init__(self):
		super().__init__()
		self._register_json_commands()
		self.set_help_text(self._get_help_text())
	
	def _register_json_commands(self):
		"""Register JSON-specific commands"""
		self.register_command("load", self._cmd_load)
		self.register_command("save", self._cmd_save)
		#self.register_command("show", self._cmd_show)
		#self.register_command("clear", self._cmd_clear)
	
	def _get_help_text(self):
		# TODO: Build help text dynamically
		return """
Available commands:
  help, ?     - Show this help message
  quit        - Exit the chat
  save        - Save the current JSON document to a file
  load        - Load a JSON document from a file
			
You can also interact with the agent by asking questions about your JSON document.
Example queries:
  - Describe the structure of this JSON
  - Add a new field to the document
  - Convert this array to an object
  - Remove the field "xyz"
	"""
	"""
	show        - Display the current JSON document
	clear       - Clear the current JSON document
	"""

	def _cmd_load(self, args, current_state={}, **kwargs):
		"""Load a JSON document from a file"""
		file_path = input("Enter JSON file path to load: ")
		try:
			file_path = Path(file_path)
			if not file_path.exists():
				log.error(f"File not found: {file_path}")
				return True
				
			with open(file_path, 'r', encoding='utf-8') as f:
				loaded_json = json.load(f)
			
			# Update the JSON document in the state
			current_state["json_doc"] = loaded_json
			current_state["initial_json_doc"] = loaded_json
			
			log.flow(f"JSON loaded from: {file_path}")
			return current_state  # Return the modified state
		except json.JSONDecodeError:
			log.error(f"Invalid JSON format in file: {file_path}")
		except Exception as e:
			log.error(f"Error loading file: {str(e)}")
		return True
	
	def _cmd_save(self, args, current_state={}, **kwargs):
		"""Save the current JSON document to a file"""
		if "json_doc" not in current_state or not current_state["json_doc"]:
			log.flow("No JSON document to save.")
			return True
			
		json_doc = current_state["json_doc"]
		current_state["saved_json_doc"] = json_doc

		if args.output:
			save_path = args.output
		else:
			save_path = input("Enter filepath to save JSON: ")

		try:
			save_path = Path(save_path)
			save_path.parent.mkdir(parents=True, exist_ok=True)
			
			with open(save_path, 'w', encoding='utf-8') as f:
				json.dump(json_doc, f, indent=2)
				log.flow(f"JSON saved to: {save_path}")
				
			return current_state
		except Exception as e:
			log.error(f"Error saving file: {str(e)}")
		return True

	def _cmd_show(self, args, current_state={}, **kwargs):
		"""Display the current JSON document"""
		if "json_doc" not in current_state or not current_state["json_doc"]:
			log.flow("No JSON document available to display.")
		else:
			log.flow("\nCurrent JSON document:")
			log.common(json.dumps(current_state["json_doc"], indent=2))
		return True
	
	def _cmd_clear(self, args, current_state={}, **kwargs):
		"""Clear the current JSON document"""
		if "json_doc" not in current_state or not current_state["json_doc"]:
			log.flow("No JSON document to clear.")
			return True
			
		confirm = input("Are you sure you want to clear the current JSON document, reverting it to initial state? (y/n): ")
		if confirm.lower() in ['y', 'yes']:
			current_state["json_doc"] = current_state["initial_json_doc"]
			log.flow("JSON document cleared.")
			return current_state
		return True 