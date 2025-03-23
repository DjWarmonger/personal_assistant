import json
import os
from pathlib import Path
import sys

# Add the parent directory to sys.path if needed
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from operations.summarize_json import adaptive_summarize, adaptive_summarize_text, format_summary_for_humans

def test_adaptive_summarization():
	"""
	Test the adaptive_summarize function with the 1mm.json file at different target sizes.
	"""
	# Path to the 1mm.json file - adjust the path as needed
	json_file_path = Path("../Agent/testFiles/1mm.json")
	
	# Check if file exists
	if not json_file_path.exists():
		print(f"Error: File not found at {json_file_path}")
		return
	
	# Load the JSON data
	with open(json_file_path, "r") as f:
		data = json.load(f)
	
	# Test with different target sizes
	target_sizes = [200, 500, 1000, 2000, 5000]
	
	results = []
	
	print(f"Original JSON size: {len(json.dumps(data))} characters\n")
	
	for target_size in target_sizes:
		summary, depth = adaptive_summarize_text(data, target_size, pretty_output=True)
		summary_size = len(summary)
		
		results.append({
			"target_size": target_size,
			"actual_size": summary_size,
			"depth_used": depth,
			"summary": summary
		})
		
		print(f"Target size: {target_size} characters")
		print(f"Actual size: {summary_size} characters")
		print(f"Depth used: {depth}")
		print("Summary preview:")
		print(summary)  # Print the formatted summary directly, don't convert to JSON string
		print("-" * 80)
	
	# Output the smallest and largest summaries for comparison
	smallest = results[0]
	largest = results[-1]
	
	print("\nSmallest summary (depth={}):\n".format(smallest["depth_used"]))
	print(smallest["summary"])  # Print directly, don't use json.dumps
	
	print("\nLargest summary (depth={}):\n".format(largest["depth_used"]))
	# Show only the first portion of the large summary
	print("\n".join(largest["summary"].split("\n")[:30]))
	print("...")

if __name__ == "__main__":
	test_adaptive_summarization() 