from typing import Dict, List, Optional, Set
from tz_common import CustomUUID
from pydantic.v1 import BaseModel, Field, PrivateAttr

from tz_common import log

class BlockTree(BaseModel):
	parents: Dict[CustomUUID, CustomUUID] = Field(default_factory=dict)
	children: Dict[CustomUUID, List[CustomUUID]] = Field(default_factory=dict)

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

	def add_relationship(self, parent_uuid: CustomUUID, child_uuid: CustomUUID) -> None:
		"""Add a parent-child relationship between blocks"""
		# Add to parents dict
		parent_changed = self.parents.get(child_uuid) != parent_uuid
		self.parents[child_uuid] = parent_uuid

		# Add to children dict
		children_changed = False
		if parent_uuid not in self.children:
			self.children[parent_uuid] = []
			children_changed = True
		if child_uuid not in self.children[parent_uuid]:
			self.children[parent_uuid].append(child_uuid)
			children_changed = True

		if parent_changed or children_changed:
			#log.debug(f"Added relationship to tree: {parent_uuid} -> {child_uuid}")
			pass


	def add_relationships(self, parent_uuid: CustomUUID, child_uuids: List[CustomUUID]) -> None:
		"""Add multiple children to a parent"""
		for child_uuid in child_uuids:
			self.add_relationship(parent_uuid, child_uuid)


	def add_parent(self, parent_uuid: CustomUUID) -> None:
		"""Add a parent block, might be root with no children"""
		if parent_uuid not in self.children:
			self.children[parent_uuid] = []
			#log.debug(f"Added parent to tree: {parent_uuid}")

		# FIXME: What is this "parent is not actually a root"?


	def get_parent(self, uuid: CustomUUID) -> Optional[CustomUUID]:
		"""Get parent UUID of a block"""
		return self.parents.get(uuid)


	def get_children(self, uuid: CustomUUID) -> List[CustomUUID]:
		"""Get children UUIDs of a block"""
		return self.children.get(uuid, [])


	def get_all_children_recursive(self, uuid: CustomUUID) -> List[CustomUUID]:
		"""Get all children UUIDs of a block, recursively"""
		all_children: Set[CustomUUID] = set()
		to_process = [uuid]
		processed_for_children = set() # To avoid processing children of the initial uuid if it's part of its own descendants

		# First, gather direct children of the starting uuid
		# This ensures that if uuid is part of a cycle that doesn't include itself as a direct child,
		# its direct children are still processed.
		direct_children_of_start_node = self.get_children(uuid)
		
		queue = list(direct_children_of_start_node)
		
		while queue:
			current_uuid = queue.pop(0)
			if current_uuid not in all_children: # Avoid processing the same node multiple times
				all_children.add(current_uuid)
				# Add children of the current_uuid to the queue
				# This will explore deeper into the tree.
				grandchildren = self.get_children(current_uuid)
				for grandchild in grandchildren:
					if grandchild not in all_children: # Add to queue only if not already collected
						queue.append(grandchild)
		return list(all_children)


	def get_siblings(self, uuid: CustomUUID) -> List[CustomUUID]:
		"""Get sibling UUIDs of a block"""
		parent = self.get_parent(uuid)
		if parent is None:
			return []
		
		siblings = self.get_children(parent)
		return [s for s in siblings if s != uuid]


	def get_all_parents(self, uuid: CustomUUID) -> List[CustomUUID]:
		"""Get all ancestor UUIDs of a block, from immediate parent to the root"""
		ancestors: List[CustomUUID] = []
		current_uuid = uuid
		while True:
			parent = self.get_parent(current_uuid)
			if parent is None:
				break
			ancestors.append(parent)
			if parent == current_uuid: # Cycle detected
				log.warning(f"Cycle detected for UUID {current_uuid} in get_all_parents")
				break
			current_uuid = parent
		return ancestors


	def get_roots(self) -> List[CustomUUID]:
		"""Get all root nodes (blocks with no parents)"""
		all_nodes = self.get_all_nodes()
		return [uuid for uuid in all_nodes if uuid not in self.parents]
	

	def get_all_nodes(self) -> List[CustomUUID]:
		"""Get all nodes in the tree"""
		# Flatten children values (lists) into a single set
		children_nodes = set()
		for children_list in self.children.values():
			children_nodes.update(children_list)

		# Parents without children are possible, but children always have parents
		return list(set(self.parents.values()) | self.parents.keys() | children_nodes | self.children.keys())


	def get_tree_str(self, titles: Optional[Dict[CustomUUID, str]] = None) -> str:
		"""
		Print tree structure similar to Linux 'tree' command
		titles: Optional dict mapping UUIDs to display names
		"""
		if not titles:
			titles = {}

		def _get_tree_lines(uuid: CustomUUID, prefix: str = "", is_last: bool = True) -> List[str]:
			lines = []
			
			# Get display name or use full UUID
			name = titles.get(uuid, str(uuid))
			
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


	def remove_relationship(self, parent_uuid: CustomUUID, child_uuid: CustomUUID) -> None:
		"""Remove a parent-child relationship"""
		removed = False
		if child_uuid in self.parents and self.parents[child_uuid] == parent_uuid: # Ensure correct parent is being removed
			del self.parents[child_uuid]
			removed = True

		if parent_uuid in self.children:
			if child_uuid in self.children[parent_uuid]:
				self.children[parent_uuid].remove(child_uuid)
				# If the parent has no more children after removal, remove the parent from children dict
				if not self.children[parent_uuid]:
					del self.children[parent_uuid]
				removed = True
		
		if removed:
			#log.debug(f"Removed relationship from tree: {parent_uuid} -> {child_uuid}")
			pass

	def remove_block_and_its_relationships(self, root_uuid: CustomUUID) -> None: # Renamed from remove_subtree
		"""Remove a node and all its descendants, and its relationship with its parent."""
		# First, remove the relationship from its parent
		parent = self.get_parent(root_uuid)
		if parent:
			self.remove_relationship(parent, root_uuid)
			# If root_uuid was the only child of 'parent', 'parent' might now be an empty entry in self.children
			# remove_relationship should handle cleaning up empty self.children[parent] list.

		# Now, gather all descendants of root_uuid
		descendants_to_remove: Set[CustomUUID] = set()
		to_process = [root_uuid] # Start with the root_uuid itself
		
		processed_nodes: Set[CustomUUID] = set()

		while to_process:
			current = to_process.pop(0)
			if current in processed_nodes:
				continue
			processed_nodes.add(current)
			
			descendants_to_remove.add(current)
			
			# Add direct children to process queue
			# Make a copy of children list for safe iteration if modification occurs
			children_of_current = list(self.get_children(current))
			for child in children_of_current:
				if child not in processed_nodes:
					to_process.append(child)

		# Remove all collected nodes (root_uuid and its descendants)
		for uuid_to_remove in descendants_to_remove:
			# Remove from parents dict (where uuid_to_remove is a child)
			if uuid_to_remove in self.parents:
				del self.parents[uuid_to_remove]
			
			# Remove from children dict (where uuid_to_remove is a parent)
			if uuid_to_remove in self.children:
				del self.children[uuid_to_remove]

			# Also, iterate through all other parents in self.children
			# to remove uuid_to_remove if it appears in any child list.
			# This is important if a node was a child of multiple parents (not typical in this tree model, but defensive)
			# or if its original parent was already handled but it might linger elsewhere due to complex ops.
			# However, standard tree structure implies one parent, so this part might be redundant
			# if remove_relationship and initial parent link removal are solid.
			# For now, the above deletions (from self.parents and as a key in self.children)
			# should be sufficient for a standard tree.

		if descendants_to_remove:
			#log.debug(f"Removed block and its relationships from tree: {root_uuid} and {len(descendants_to_remove)-1} descendants")
			pass


	def is_empty(self):
		return not self.parents and not self.children
		
	# New methods for serialization support
	def to_dict(self) -> dict:
		"""Convert the tree to a dictionary for serialization"""
		return self.model_dump()
	
	@classmethod
	def from_dict(cls, data: dict) -> 'BlockTree':
		"""Create a BlockTree from serialized dictionary using Pydantic parsing."""
		log.debug(f"BlockTree.from_dict received data for Pydantic parsing (type: {type(data)}): {data}")
		
		if not isinstance(data, dict):
			log.error(f"BlockTree.from_dict: Expected dict for data, got {type(data)}. Returning empty tree.")
			return cls() # Return empty BlockTree

		# Ensure basic structure for Pydantic parsing; Pydantic will handle missing fields if defaults exist
		# or raise validation error if required fields are missing and not in input.
		# The fields 'parents' and 'children' have default_factory=dict, so they are not strictly required in 'data'
		# for cls(**data) to be called, but good to check for sanity.
		if "parents" not in data:
			log.debug("BlockTree.from_dict: 'parents' key missing in input data, will use default_factory.")
			data["parents"] = {} # Ensure key exists if not provided, for robustness if default_factory not enough
		
		if "children" not in data:
			log.debug("BlockTree.from_dict: 'children' key missing in input data, will use default_factory.")
			data["children"] = {} # Ensure key exists

		try:
			# Pydantic will use __get_validators__ in CustomUUID to parse string keys/values.
			# The input 'data' should have string keys and string values (or list of strings for children values).
			instance = cls(**data) # equivalent to cls.parse_obj(data) for V1 basic cases
			log.debug(f"BlockTree.from_dict successfully created instance via Pydantic: {instance.parents}, {instance.children}")
			return instance
		except Exception as e: # Catch Pydantic ValidationError or any other during instantiation
			log.error(f"CRITICAL: Error during BlockTree Pydantic instantiation from_dict: {e}", exc_info=True)
			log.error(f"Data that caused error: {data}")
			# Decide on fallback: return empty tree or re-raise
			# For safety, return an empty tree if parsing fails, to prevent cascading errors.
			# The calling code might need to handle this possibility.
			return cls()
	
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
		# Convert CustomUUID objects back to strings for serialization
		parents_str = {str(k): str(v) for k, v in self.parents.items()}
		children_str = {str(k): [str(v) for v in v_list] for k, v_list in self.children.items()}
		
		return {
			"parents": parents_str,
			"children": children_str
		}
