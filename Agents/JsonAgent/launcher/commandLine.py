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

from tz_common.logs import log
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
		default="Process this JSON document",
		help="Initial prompt to send to the agent"
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
					log.info(f"Loaded JSON from file: {input_path}")
			else:
				# Try to parse as JSON string
				input_json = json.loads(args.input)
				log.info("Parsed JSON from command line argument")
		except json.JSONDecodeError:
			log.error(f"Failed to parse JSON from: {args.input}")
			sys.exit(1)
		except Exception as e:
			log.error(f"Error processing input: {str(e)}")
			sys.exit(1)
	
	# Call the chat function with the JSON document and without looping
	response = chat(
		loop=False,
		user_prompt=args.prompt,
		initial_json=input_json
	)
	
	# Get final JSON from JsonAgent
	from ..Agent.graph import json_agent
	
	# Get the current state to extract the final JSON
	# Note: This is a bit of a hack since we don't have direct access to the final state
	graph_state = json_agent.get_state()
	if graph_state:
		final_json = graph_state.get("final_json_doc", graph_state.get("json_doc", input_json))
	else:
		final_json = input_json
	
	# Save output JSON if specified
	if args.output:
		try:
			output_path = Path(args.output)
			output_path.parent.mkdir(parents=True, exist_ok=True)
			
			with open(output_path, 'w', encoding='utf-8') as f:
				json.dump(final_json, f, indent=2)
				log.info(f"Saved processed JSON to: {output_path}")
		except Exception as e:
			log.error(f"Error saving output: {str(e)}")
			sys.exit(1)
	else:
		# Print the final JSON if no output file specified
		print("\nFinal JSON:")
		print(json.dumps(final_json, indent=2))


if __name__ == "__main__":
	main() 