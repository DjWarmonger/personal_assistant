from typing import Dict, Any
from pydantic.v1 import BaseModel, Field


class BlockDict(BaseModel):
	"""
	Pydantic model representing a mapping of integer block IDs to their content.
	This provides a clean int id -> block content mapping without nesting.
	"""
	
	blocks: Dict[int, Dict[str, Any]] = Field(
		default_factory=dict,
		description="Mapping of integer block IDs to their content dictionaries"
	)

	class Config:
		# Enable JSON serialization by allowing the model to be converted to dict
		arbitrary_types_allowed = True


	def dict(self, **kwargs):
		"""Override dict() method to return the blocks directly for JSON serialization."""
		return self.blocks


	def __getitem__(self, key: int) -> Dict[str, Any]:
		"""Allow dictionary-style access to blocks."""
		return self.blocks[key]


	def __setitem__(self, key: int, value: Dict[str, Any]) -> None:
		"""Allow dictionary-style assignment to blocks."""
		self.blocks[key] = value


	def __contains__(self, key: int) -> bool:
		"""Check if a block ID exists in the collection."""
		return key in self.blocks


	def __len__(self) -> int:
		"""Return the number of blocks."""
		return len(self.blocks)


	def __iter__(self):
		"""Allow iteration over block IDs."""
		return iter(self.blocks)


	def items(self):
		"""Return items like a regular dict."""
		return self.blocks.items()


	def keys(self):
		"""Return keys like a regular dict."""
		return self.blocks.keys()


	def values(self):
		"""Return values like a regular dict."""
		return self.blocks.values()


	def get(self, key: int, default=None):
		"""Get a block with optional default value."""
		return self.blocks.get(key, default)


	def update(self, other_dict: Dict[int, Dict[str, Any]]) -> None:
		"""Update blocks with another dictionary."""
		self.blocks.update(other_dict)


	def add_block(self, block_id: int, content: Dict[str, Any]) -> None:
		"""Add a single block to the collection."""
		self.blocks[block_id] = content


	def to_dict(self) -> Dict[int, Dict[str, Any]]:
		"""Convert to a regular dictionary."""
		return self.blocks.copy() 