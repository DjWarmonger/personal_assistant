"""
Entry point module for the launcher package.
This allows running the package directly with 'python -m Agents.JsonAgent.launcher'
"""

import sys

if __name__ == "__main__":
	from .chat import chat
	chat() 