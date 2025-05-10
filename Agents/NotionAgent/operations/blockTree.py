from typing import Dict, List, Optional, Set
from .uuid_converter import UUIDConverter
from pydantic.v1 import BaseModel, Field, PrivateAttr

from tz_common.logs import log

# FIXME: Move conversion to dedicated UUID class, no need to create extra converter object

converter = UUIDConverter()

class BlockTree(BaseModel):
	parents: Dict[str, str] = Field(default_factory=dict)
	children: Dict[str, List[str]] = Field(default_factory=dict)

	"""
	Example usage:

	tree = BlockTree()
	tree.add_relationship("parent1", "child1")
	tree.add_relationship("parent1", "child2")
	tree.add_relationships("child1", ["grandchild1", "grandchild2"])

	# Print with UUIDs
	print(tree.get_tree_str())

	# Print with custom titles
	titles = {
		"parent1": "Home Page",
		"child1": "Projects",
		"child2": "Notes"
	}
	print(tree.get_tree_str(titles))
	"""

	def add_relationship(self, parent_uuid: str, child_uuid: str) -> None:
		"""Add a parent-child relationship between blocks"""
		parent_uuid = converter.clean_uuid(parent_uuid)
		child_uuid = converter.clean_uuid(child_uuid)

		# Add to parents dict
		self.parents[child_uuid] = parent_uuid

		# Add to children dict
		if parent_uuid not in self.children:
			self.children[parent_uuid] = []
		if child_uuid not in self.children[parent_uuid]:
			self.children[parent_uuid].append(child_uuid)

		log.debug(f"Added relationship to tree: {parent_uuid} -> {child_uuid}")


	def add_relationships(self, parent_uuid: str, child_uuids: List[str]) -> None:
		"""Add multiple children to a parent"""
		for child_uuid in child_uuids:
			self.add_relationship(parent_uuid, child_uuid)


	def add_parent(self, parent_uuid: str) -> None:
		"""Add a parent block, might be root with no children"""
		parent_uuid = converter.clean_uuid(parent_uuid)

		if parent_uuid not in self.children:
			self.children[parent_uuid] = []

		log.debug(f"Added parent to tree: {parent_uuid}")

		# FIXME: What is this "parent is not actually a root"?


	def get_parent(self, uuid: str) -> Optional[str]:
		"""Get parent UUID of a block"""
		uuid = converter.clean_uuid(uuid)
		return self.parents.get(uuid)


	def get_children(self, uuid: str) -> List[str]:
		"""Get children UUIDs of a block"""
		uuid = converter.clean_uuid(uuid)
		return self.children.get(uuid, [])


	def get_roots(self) -> List[str]:
		"""Get all root nodes (blocks with no parents)"""
		all_nodes = self.get_all_nodes()
		return [uuid for uuid in all_nodes if uuid not in self.parents]
	

	def get_all_nodes(self) -> List[str]:
		"""Get all nodes in the tree"""
		# Flatten children values (lists) into a single set
		children_nodes = set()
		for children_list in self.children.values():
			children_nodes.update(children_list)

		# Parents without children are possible, but children always have parents
		return list(set(self.parents.values()) | self.parents.keys() | children_nodes | self.children.keys())


	def get_tree_str(self, titles: Optional[Dict[str, str]] = None) -> str:
		"""
		Print tree structure similar to Linux 'tree' command
		titles: Optional dict mapping UUIDs to display names
		"""
		if not titles:
			titles = {}

		def _get_tree_lines(uuid: str, prefix: str = "", is_last: bool = True) -> List[str]:
			lines = []
			
			# Get display name or use full UUID
			name = titles.get(uuid, uuid)
			
			# Add current node with no trailing spaces
			if prefix:
				marker = "└──" if is_last else "├──"
				lines.append(f"{prefix}{marker}{name}".rstrip())
			else:
				lines.append(str(name).rstrip())

			# Recursively add children
			children = self.get_children(uuid)
			if not children:
				return lines

			new_prefix = prefix + ("   " if is_last else "│  ")
			for i, child in enumerate(children):
				is_last_child = (i == len(children) - 1)
				lines.extend(_get_tree_lines(child, new_prefix, is_last_child))

			return lines

		# Build tree starting from all roots
		roots = self.get_roots()
		if not roots:
			return "Empty tree"

		all_lines = []
		for i, root in enumerate(roots):
			is_last_root = (i == len(roots) - 1)
			all_lines.extend(_get_tree_lines(root, "", is_last_root))

		# Join lines and ensure no trailing whitespace
		return "\n".join(line.rstrip() for line in all_lines)
	

	def __str__(self):
		return self.get_tree_str()


	def remove_relationship(self, parent_uuid: str, child_uuid: str) -> None:
		"""Remove a parent-child relationship"""
		parent_uuid = converter.clean_uuid(parent_uuid)
		child_uuid = converter.clean_uuid(child_uuid)

		if child_uuid in self.parents:
			del self.parents[child_uuid]

		if parent_uuid in self.children:
			if child_uuid in self.children[parent_uuid]:
				self.children[parent_uuid].remove(child_uuid)
			if not self.children[parent_uuid]:
				del self.children[parent_uuid]

		#log.debug(f"Removed relationship from tree: {parent_uuid} -> {child_uuid}")

	def remove_subtree(self, root_uuid: str) -> None:
		"""Remove a node and all its descendants"""
		root_uuid = converter.clean_uuid(root_uuid)
		
		# First get all descendants
		to_remove = set()
		to_process = [root_uuid]
		
		while to_process:
			current = to_process.pop()
			to_remove.add(current)
			to_process.extend(self.get_children(current))

		# Remove all relationships involving these nodes
		for uuid in to_remove:
			if uuid in self.parents:
				parent = self.parents[uuid]
				self.remove_relationship(parent, uuid)
			
			if uuid in self.children:
				for child in self.children[uuid][:]:  # Copy list since we're modifying it
					self.remove_relationship(uuid, child)

		#log.debug(f"Removed subtree from tree: {root_uuid}")

	def is_empty(self):
		return not self.parents and not self.children
		
	# New methods for serialization support
	def to_dict(self) -> dict:
		"""Convert the tree to a dictionary for serialization"""
		return self.model_dump()
	
	@classmethod
	def from_dict(cls, data: dict) -> 'BlockTree':
		"""Create a BlockTree from serialized dictionary"""
		if not isinstance(data, dict):
			log.error(f"Expected dict, got {type(data)}")
			return cls()
			
		if "parents" not in data or "children" not in data:
			log.error(f"Invalid BlockTree data, missing parents or children")
			return cls()
			
		return cls(parents=data.get("parents", {}), children=data.get("children", {}))
	
	def __eq__(self, other):
		if not isinstance(other, BlockTree):
			return False
		return self.parents == other.parents and self.children == other.children
	
	def __hash__(self):
		parents_fs = frozenset((k, v) for k, v in self.parents.items())
		children_fs = frozenset((k, frozenset(v)) for k, v in self.children.items())
		return hash((parents_fs, children_fs))

	def model_dump(self, **kwargs):
		"""Custom JSON serialization method to ensure proper serialization in state"""
		return {
			"parents": self.parents,
			"children": self.children
		}
