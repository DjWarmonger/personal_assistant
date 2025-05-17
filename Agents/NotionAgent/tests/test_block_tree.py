import unittest
import sys
import os
from typing import Dict, List
from unittest.mock import patch

# Update the import path to include the project root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Use direct imports from operations
from operations.blockTree import BlockTree
from tz_common import CustomUUID # Updated import

# Predefined valid UUIDs for testing
TEST_PARENT_UUID_1 = "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11"
TEST_CHILD_UUID_1 = "0c7cb43c-09a6-45a8-9320-573189f0f8f4"
TEST_CHILD_UUID_2 = "3d5b7a21-3056-4ea8-9dc0-301778710c55"
TEST_GRANDCHILD_UUID_1 = "ef2f8a2c-12cc-473c-8b32-9f721070670c"
TEST_GRANDCHILD_UUID_2 = "abf39c9f-7cbf-4cea-8d83-1e05e417e047"
TEST_PARENT_UUID_2 = "fabdd1a3-cf08-49a5-819b-895819789359"
TEST_CHILD_UUID_3 = "acde070d-8c4c-4f0d-9d8a-162843c10333"

class TestBlockTree(unittest.TestCase):
	def setUp(self):
		self.tree = BlockTree()
		# Convert string UUIDs to CustomUUID objects before adding
		self.parent1 = CustomUUID.from_string(TEST_PARENT_UUID_1)
		self.child1 = CustomUUID.from_string(TEST_CHILD_UUID_1)
		self.child2 = CustomUUID.from_string(TEST_CHILD_UUID_2)
		self.grandchild1 = CustomUUID.from_string(TEST_GRANDCHILD_UUID_1)
		self.grandchild2 = CustomUUID.from_string(TEST_GRANDCHILD_UUID_2)
		self.parent2 = CustomUUID.from_string(TEST_PARENT_UUID_2)
		self.child3 = CustomUUID.from_string(TEST_CHILD_UUID_3)

		self.tree.add_relationship(self.parent1, self.child1)
		self.tree.add_relationship(self.parent1, self.child2)
		self.tree.add_relationships(self.child1, [self.grandchild1, self.grandchild2])


	def test_add_single_relationship(self):
		self.tree.add_relationship(self.parent2, self.child3)
		self.assertIn(self.child3, self.tree.children[self.parent2])
		self.assertEqual(self.tree.parents[self.child3], self.parent2)


	def test_add_multiple_relationships(self):
		# This is already tested in setUp, but we can add more specific assertions
		self.assertIn(self.child1, self.tree.children[self.parent1])
		self.assertIn(self.child2, self.tree.children[self.parent1])
		self.assertEqual(self.tree.parents[self.child1], self.parent1)
		self.assertEqual(self.tree.parents[self.child2], self.parent1)


	def test_get_children(self):
		children = self.tree.get_children(self.parent1)
		self.assertIn(self.child1, children)
		self.assertIn(self.child2, children)
		self.assertEqual(len(children), 2)


	def test_get_parent(self):
		parent = self.tree.get_parent(self.child1)
		self.assertEqual(parent, self.parent1)


	def test_get_siblings(self):
		siblings = self.tree.get_siblings(self.child1)
		self.assertIn(self.child2, siblings)
		self.assertEqual(len(siblings), 1)


	def test_get_all_parents(self):
		all_parents = self.tree.get_all_parents(self.grandchild1)
		# Expected: [child1, parent1]
		self.assertEqual(len(all_parents), 2)
		# Order is child1, then parent1 because we traverse up
		self.assertIn(self.child1, all_parents)
		self.assertIn(self.parent1, all_parents)
		self.assertEqual(all_parents[0], self.child1)
		self.assertEqual(all_parents[1], self.parent1)


	def test_get_all_children(self):
		all_children = self.tree.get_all_children_recursive(self.parent1)
		# Expected to find child1, child2, grandchild1, grandchild2
		self.assertIn(self.child1, all_children)
		self.assertIn(self.child2, all_children)
		self.assertIn(self.grandchild1, all_children)
		self.assertIn(self.grandchild2, all_children)
		self.assertEqual(len(all_children), 4)


	def test_get_tree_str_no_titles(self):
		# Test the structure of the output string, not exact content due to UUIDs
		tree_str = self.tree.get_tree_str()
		self.assertIn(str(self.parent1), tree_str) 
		self.assertIn(str(self.child1), tree_str)
		self.assertIn(str(self.grandchild1), tree_str)
		# Check for indentation (presence of tabs or spaces for levels)
		child_line = [line for line in tree_str.split('\n') if str(self.child1) in line][0]
		grandchild_line = [line for line in tree_str.split('\n') if str(self.grandchild1) in line][0]
		# child1 line: "   ├──child1_name..." (child1 is not last child of parent1)
		self.assertTrue(child_line.startswith('   ')) # Expects 3 leading spaces for child1
		# grandchild1 line: "   │  ├──grandchild1_name..." (grandchild1 is not last child of child1, and child1 is not last child of parent1)
		self.assertTrue(grandchild_line.startswith('   │  ')) # Expects this specific prefix


	def test_get_tree_str_with_titles(self):
		titles = {
			str(self.parent1): "Home Page",
			str(self.child1): "Projects",
			str(self.grandchild1): "Project Alpha"
		}
		tree_str = self.tree.get_tree_str(titles=titles)
		self.assertIn("Home Page", tree_str)
		self.assertIn("Projects", tree_str)
		self.assertIn("Project Alpha", tree_str)


	def test_remove_relationship(self):
		self.tree.remove_relationship(self.parent1, self.child1)
		self.assertNotIn(self.child1, self.tree.children.get(self.parent1, []))
		self.assertIsNone(self.tree.parents.get(self.child1))
		# Grandchildren of child1 should also be effectively orphaned from parent1's direct tree view
		# but direct parent of grandchild1 should still be child1 if child1 object itself wasn't removed from all contexts
		# The following assertion might fail if child1 is completely removed, which it shouldn't be by remove_relationship only.
		# Child1's own children list should remain intact if it were a standalone tree.
		# Let's check that grandchild1 is not a descendant of parent1 anymore.
		self.assertNotIn(self.grandchild1, self.tree.get_all_children_recursive(self.parent1))


	def test_remove_block_and_its_relationships(self):
		# Add another branch to ensure only target block is removed
		parent3 = CustomUUID.from_string("c33a9a88-3068-4ea1-7dc0-101778110c33")
		child4 = CustomUUID.from_string("d44b9b11-4076-5eb2-8ed1-201778710d44")
		self.tree.add_relationship(parent3, child4)

		self.tree.remove_block_and_its_relationships(self.child1)
		# child1 should be gone from parent1's children
		self.assertNotIn(self.child1, self.tree.children.get(self.parent1, []))
		# child1 should be gone from parents dict
		self.assertNotIn(self.child1, self.tree.parents)
		# child1 should be gone from children dict as a parent
		self.assertNotIn(self.child1, self.tree.children)
		# Grandchildren of child1 (grandchild1, grandchild2) should also be removed from tree structure
		self.assertNotIn(self.grandchild1, self.tree.parents)
		self.assertNotIn(self.grandchild2, self.tree.parents)
		# Other relationships should remain
		self.assertIn(self.child2, self.tree.children.get(self.parent1, []))
		self.assertIn(child4, self.tree.children.get(parent3, []))


	def test_serialization_round_trip(self):
		# tree is already populated from setUp
		d = self.tree.to_dict()
		tree2 = BlockTree.from_dict(d)
		self.assertEqual(self.tree.parents, tree2.parents)
		self.assertEqual(self.tree.children, tree2.children)


	def test_get_roots(self):
		self.tree.add_relationship(self.parent2, self.child3) # parent2 is another root
		roots = self.tree.get_roots()
		self.assertIn(self.parent1, roots)
		self.assertIn(self.parent2, roots)
		self.assertEqual(len(roots), 2)


	def test_duplicate_relationships(self):
		initial_children_count = len(self.tree.get_children(self.parent1))
		# Add an existing relationship again
		self.tree.add_relationship(self.parent1, self.child1)
		# The number of children for parent1 should not change
		self.assertEqual(len(self.tree.get_children(self.parent1)), initial_children_count)
		# Ensure child1 still has parent1 as its parent (and not duplicated or altered)
		self.assertEqual(self.tree.get_parent(self.child1), self.parent1)


	def test_empty_tree_is_empty(self):
		empty_tree = BlockTree()
		self.assertTrue(empty_tree.is_empty(), "Newly created BlockTree should be empty")
		self.assertFalse(self.tree.is_empty(), "BlockTree populated in setUp should not be empty")


	def test_empty_tree_get_tree_str(self):
		empty_tree = BlockTree()
		self.assertEqual(empty_tree.get_tree_str(), "Empty tree")


	def test_from_dict_empty(self):
		# Test with completely empty dict
		empty_data = {}
		tree_from_empty = BlockTree.from_dict(empty_data)
		self.assertTrue(tree_from_empty.is_empty(), "Tree from completely empty dict should be empty")
		self.assertEqual(tree_from_empty.parents, {})
		self.assertEqual(tree_from_empty.children, {})

		# Test with dict having empty 'parents' and 'children' keys
		empty_fields_data = {"parents": {}, "children": {}}
		tree_from_empty_fields = BlockTree.from_dict(empty_fields_data)
		self.assertTrue(tree_from_empty_fields.is_empty(), "Tree from dict with empty fields should be empty")
		self.assertEqual(tree_from_empty_fields.parents, {})
		self.assertEqual(tree_from_empty_fields.children, {})
		
		# Test with dict missing 'children' key (should use default_factory)
		missing_children_data = {"parents": {}}
		tree_missing_children = BlockTree.from_dict(missing_children_data)
		self.assertTrue(tree_missing_children.is_empty(), "Tree from dict missing 'children' should be empty")
		self.assertEqual(tree_missing_children.parents, {})
		self.assertEqual(tree_missing_children.children, {})

		# Test with dict missing 'parents' key (should use default_factory)
		missing_parents_data = {"children": {}}
		tree_missing_parents = BlockTree.from_dict(missing_parents_data)
		self.assertTrue(tree_missing_parents.is_empty(), "Tree from dict missing 'parents' should be empty")
		self.assertEqual(tree_missing_parents.parents, {})
		self.assertEqual(tree_missing_parents.children, {})


if __name__ == '__main__':
	unittest.main()
