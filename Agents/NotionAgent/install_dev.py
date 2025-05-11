#!/usr/bin/env python
"""
This script installs the NotionAgent package in development mode.
Run this script once after cloning the repository to enable imports
from any directory.
"""
import subprocess
import sys
import os

def main():
	script_dir = os.path.dirname(os.path.abspath(__file__))
	os.chdir(script_dir)
	
	print("Installing NotionAgent package in development mode...")
	result = subprocess.run([sys.executable, "-m", "pip", "install", "-e", "."], 
		capture_output=True, text=True)
	
	if result.returncode == 0:
		print("Installation successful!")
		print(f"Package installed at: {script_dir}")
		print("\nYou can now import the package from anywhere using:")
		print("  import notion_agent")
		print("  from notion_agent import NotionClient")
	else:
		print("Installation failed with the following error:")
		print(result.stderr)
	
	return result.returncode

if __name__ == "__main__":
	sys.exit(main()) 