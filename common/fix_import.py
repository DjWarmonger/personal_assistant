import zipfile
from pathlib import Path
import sys

def extract_egg(egg_path: str, extract_to: str = None) -> Path:
	"""
	Extracts a .egg file to a specified location.

	:param egg_path: Path to the .egg file
	:param extract_to: Directory to extract the contents. Defaults to the egg's directory.
	:return: The path where the egg was extracted
	"""
	# Use __file__ to create an absolute path
	script_dir = Path(__file__).parent.resolve()
	egg_path = script_dir / egg_path  # Construct the path relative to the script

	egg_path = egg_path.resolve()
	if not egg_path.exists() or egg_path.suffix != '.egg':
		print("The specified .egg file does not exist.")
		return None

	if extract_to is None:
		extract_to = egg_path.with_suffix('')  # Remove .egg extension for folder name
	else:
		extract_to = Path(extract_to).resolve()

	# Create extract directory if it does not exist
	extract_to.mkdir(parents=True, exist_ok=True)

	# Extract the egg file
	with zipfile.ZipFile(egg_path, 'r') as egg_zip:
		egg_zip.extractall(extract_to)

	# Print the extraction result
	print(f"Extracted {egg_path} to {extract_to}.")
	return extract_to

# Example Usage:
# Make sure to replace 'dist/tz_common-0.3-py3.10.egg' with your actual .egg file path relative to this script
extract_egg('dist/tz_common-0.3-py3.10.egg')