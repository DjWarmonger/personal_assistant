"""
CRUD operations for JSON documents.
"""

from .search import search_json
from .modify import modify_json
from .add import add_to_json
from .delete import delete_from_json
from .info import get_json_info

__all__ = [
	'search_json',
	'modify_json',
	'add_to_json',
	'delete_from_json',
	'get_json_info'
] 