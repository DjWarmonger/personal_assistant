"""
Custom exception types for NotionAgent operations.
Provides structured error handling without relying on exception messages.
"""

from typing import Optional


class NotionServiceError(Exception):
	"""Base exception for NotionService operations."""
	pass


class InvalidUUIDError(NotionServiceError):
	"""Raised when an invalid UUID is provided."""
	
	def __init__(self, uuid_value: str):
		self.uuid_value = uuid_value
		super().__init__(f"Invalid UUID: {uuid_value}")


class BlockTreeRequiredError(NotionServiceError):
	"""Raised when a block tree is required but not provided."""
	
	def __init__(self, operation: str):
		self.operation = operation
		super().__init__(f"BlockTree is required for operation: {operation}")


class CacheRetrievalError(NotionServiceError):
	"""Raised when cache retrieval fails."""
	
	def __init__(self, resource_type: str, resource_id: str):
		self.resource_type = resource_type
		self.resource_id = resource_id
		super().__init__(f"Failed to retrieve {resource_type}: {resource_id}")


class APIError(NotionServiceError):
	"""Raised when API calls fail."""
	
	def __init__(self, operation: str, original_error: Optional[Exception] = None):
		self.operation = operation
		self.original_error = original_error
		super().__init__(f"API error during {operation}")


class ObjectTypeVerificationError(NotionServiceError):
	"""Raised when object type verification fails."""
	
	def __init__(self, uuid_value: str, expected_type: str, actual_type: str):
		self.uuid_value = uuid_value
		self.expected_type = expected_type
		self.actual_type = actual_type
		super().__init__(f"Object {uuid_value} expected to be {expected_type} but is {actual_type}")


class RecursionLimitError(NotionServiceError):
	"""Raised when recursion limit is reached during children retrieval."""
	
	def __init__(self, block_id: str, depth: int):
		self.block_id = block_id
		self.depth = depth
		super().__init__(f"Recursion limit reached for block {block_id} at depth {depth}") 