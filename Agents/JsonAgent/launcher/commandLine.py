import argparse
import json
import sys
from pathlib import Path

# Enable relative imports when running as a script
if __name__ == "__main__":
	# Add parent directory to path to make this file importable
	current_dir = Path(__file__).parent.absolute()
	parent_dir = current_dir.parent
	
	if str(parent_dir) not in sys.path:
		sys.path.insert(0, str(parent_dir))
	
	# Set the package name for relative imports
	__package__ = "launcher"

#from tz_common.logs import log
from tz_common import log
from .chat import chat

def main():
	parser = argparse.ArgumentParser(
		description="JsonAgent CLI - Process JSON documents via command line",
		formatter_class=argparse.ArgumentDefaultsHelpFormatter
	)
	
	parser.add_argument(
		"--input", "-i",
		type=str,
		help="Input JSON file path or JSON string"
	)
	
	parser.add_argument(
		"--output", "-o",
		type=str,
		help="Output file path to save the processed JSON"
	)
	
	parser.add_argument(
		"--prompt", "-p",
		type=str,
		default="Describe the structure of this JSON document",
		help="Initial prompt to send to the agent"
	)

	parser.add_argument(
		"--interactive", "-I",
		action="store_true",
		help="Run in interactive mode with looping"
	)
	
	args = parser.parse_args()
	
	# Parse input JSON (file or string)
	input_json = {}
	if args.input:
		try:
			# First try to parse as file path
			input_path = Path(args.input)
			if input_path.exists() and input_path.is_file():
				with open(input_path, 'r', encoding='utf-8') as f:
					input_json = json.load(f)
					log.flow(f"Loaded JSON from file: {input_path}")
			else:
				# Try to parse as JSON string
				input_json = json.loads(args.input)
				log.flow("Parsed JSON from command line argument")
		except json.JSONDecodeError:
			log.error(f"Failed to parse JSON from: {args.input}")
			sys.exit(1)
		except Exception as e:
			log.error(f"Error processing input: {str(e)}")
			sys.exit(1)
	
	# Call the chat function with the JSON document and set loop based on --interactive flag
	response = chat(
		args=args,
		loop=args.interactive,
		user_prompt=args.prompt,
		initial_json=input_json,
	)

if __name__ == "__main__":
	main() 