import json
import os
from pathlib import Path
import sys

# Add the parent directory to sys.path if needed
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from operations.summarize_json import (
	adaptive_summarize,
	adaptive_summarize_text,
	format_summary_for_humans,
	truncated_json_format,
	adaptive_truncated_json
)

def load_test_json():
	"""
	Load the test JSON file for use in tests.
	Returns the loaded JSON data or a fallback test JSON if file not found.
	"""
	# Path to the 1mm.json file - adjust the path as needed
	json_file_path = Path("../Agent/testFiles/1mm.json")
	
	# Check if file exists
	if json_file_path.exists():
		# Load the JSON data
		with open(json_file_path, "r") as f:
			return json.load(f)
	else:
		print(f"Warning: File not found at {json_file_path}, using fallback test data")
		# Fallback test JSON with nested structures and arrays
		return {
			"users": [
				{"name": "Alice", "age": 30, "email": "alice@example.com", "tags": ["admin", "active"]},
				{"name": "Bob", "age": 25, "email": "bob@example.com", "tags": ["user", "active"]},
				{"name": "Charlie", "age": 35, "email": "charlie@example.com", "tags": ["user", "inactive"]},
				{"name": "David", "age": 40, "email": "david@example.com", "tags": ["admin", "active"]},
				{"name": "Eve", "age": 28, "email": "eve@example.com", "tags": ["user", "active"]}
			],
			"configuration": {
				"options": {
					"display": {"mode": "light", "font": "Arial", "size": 12},
					"network": {"proxy": None, "timeout": 30, "retries": 3},
					"storage": {"type": "cloud", "path": "/data", "readonly": False},
					"security": {"encryption": True, "level": "high", "allow_guests": False},
					"misc": {"debug": False, "language": "en", "region": "US"}
				}
			},
			"metadata": {
				"version": "1.0",
				"created": "2023-05-15",
				"updated": "2023-05-16",
				"author": "System"
			}
		}

def test_adaptive_summarization():
	"""
	Test the adaptive_summarize function with different target sizes.
	"""
	# Load the test data
	data = load_test_json()
	
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

def test_truncated_json():
	"""
	Test the truncated JSON format function with various limit settings.
	"""
	# Load the test data
	test_json = load_test_json()
	
	print("Testing truncated JSON format functionality:\n")
	
	# Test 1: Default limits (3 array items, 5 object properties)
	json1 = truncated_json_format(test_json)
	print("Default limits (3 array items, 5 object properties):")
	print(json1)
	print("-" * 80)
	
	# Test 2: Different array and object limits
	json2 = truncated_json_format(test_json, max_array_items=2, max_object_props=3)
	print("Custom limits (2 array items, 3 object properties):")
	print(json2)
	print("-" * 80)
	
	# Test 3: Different depths
	for depth in [2, 4, 5]:
		json_output = truncated_json_format(test_json, max_depth=depth, max_array_items=3, max_object_props=10)
		print(f"Depth {depth} (with 10 object properties):")
		print(json_output)
		print("-" * 80)
	
	# Test 4: Different array/object combinations
	json3 = truncated_json_format(test_json, max_array_items=5, max_object_props=2)
	print("More arrays, fewer properties (5 array items, 2 object properties):")
	print(json3)
	print("-" * 80)
	
	# Test 5: Adaptive truncated JSON
	target_size = 500
	adaptive_json, used_depth = adaptive_truncated_json(
		test_json, 
		target_size=target_size,
		max_array_items=3, 
		max_object_props=4
	)
	
	print(f"Adaptive truncated JSON (target size: {target_size}, depth used: {used_depth}):")
	print(adaptive_json)
	print(f"Actual size: {len(adaptive_json)} characters")

if __name__ == "__main__":
	# Uncomment the test you want to run
	# test_adaptive_summarization()
	test_truncated_json() 