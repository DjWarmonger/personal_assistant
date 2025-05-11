import unittest
import sys
import os

# Update the import path to include the project root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Use direct imports from operations
from operations.blockTree import BlockTree

class TestBlockTree(unittest.TestCase):
	def setUp(self):
		self.tree = BlockTree()


	def test_add_single_relationship(self):
		self.tree.add_relationship("parent1", "child1")
		
		self.assertEqual(self.tree.get_parent("child1"), "parent1")
		self.assertEqual(self.tree.get_children("parent1"), ["child1"])


	def test_add_multiple_relationships(self):
		self.tree.add_relationships("parent1", ["child1", "child2"])
		
		self.assertEqual(self.tree.get_parent("child1"), "parent1")
		self.assertEqual(self.tree.get_parent("child2"), "parent1")
		self.assertEqual(set(self.tree.get_children("parent1")), {"child1", "child2"})


	def test_get_roots(self):
		self.tree.add_relationship("root1", "child1")
		self.tree.add_relationship("root1", "child2")
		self.tree.add_relationship("root2", "child3")
		
		roots = self.tree.get_roots()
		self.assertEqual(set(roots), {"root1", "root2"})


	def test_remove_relationship(self):
		self.tree.add_relationship("parent1", "child1")
		self.tree.add_relationship("parent1", "child2")
		
		self.tree.remove_relationship("parent1", "child1")
		
		self.assertIsNone(self.tree.get_parent("child1"))
		self.assertEqual(self.tree.get_children("parent1"), ["child2"])


	def test_remove_subtree(self):
		# Create a tree structure:
		# parent1
		# ├── child1
		# │   ├── grandchild1
		# │   └── grandchild2
		# └── child2
		
		self.tree.add_relationship("parent1", "child1")
		self.tree.add_relationship("parent1", "child2")
		self.tree.add_relationship("child1", "grandchild1")
		self.tree.add_relationship("child1", "grandchild2")
		
		self.tree.remove_subtree("child1")
		
		# Check that child1 and its descendants are removed
		self.assertIsNone(self.tree.get_parent("child1"))
		self.assertIsNone(self.tree.get_parent("grandchild1"))
		self.assertIsNone(self.tree.get_parent("grandchild2"))
		self.assertEqual(self.tree.get_children("parent1"), ["child2"])


	def test_tree_visualization(self):
		# Create a test tree
		self.tree.add_relationship("root1", "child1")
		self.tree.add_relationship("root1", "child2")
		self.tree.add_relationship("child1", "grandchild1")
		
		# Test with UUIDs
		tree_str = self.tree.get_tree_str()
		expected_lines = [
            "root1",
            "   ├──child1",
            "   │  └──grandchild1",
            "   └──child2"
		]
		self.assertEqual(tree_str, "\n".join(expected_lines))
		
		# Test with custom titles
		titles = {
			"root1": "Home",
			"child1": "Projects",
			"child2": "Notes",
			"grandchild1": "Project1"
		}
		tree_str = self.tree.get_tree_str(titles)
		expected_lines = [
            "Home",
            "   ├──Projects",
            "   │  └──Project1",
            "   └──Notes"
		]
		self.assertEqual(tree_str, "\n".join(expected_lines))


	def test_uuid_formatting(self):
		# Test that UUIDs are properly cleaned and formatted
		uuid1 = "123e4567-e89b-12d3-a456-426614174000"
		uuid2 = "123E4567E89B12D3A456426614174000"
		
		self.tree.add_relationship(uuid1, uuid2)
		
		# Both formats should work for lookup
		self.assertIsNotNone(self.tree.get_parent(uuid2))
		self.assertIsNotNone(self.tree.get_children(uuid1))


	def test_empty_tree(self):
		self.assertEqual(self.tree.get_tree_str(), "Empty tree")
		self.assertEqual(self.tree.get_roots(), [])


	def test_duplicate_relationships(self):
		# Adding same relationship multiple times should not create duplicates
		self.tree.add_relationship("parent1", "child1")
		self.tree.add_relationship("parent1", "child1")
		
		self.assertEqual(len(self.tree.get_children("parent1")), 1)


	def test_invalid_operations(self):
		# Test operations with non-existent nodes
		self.assertEqual(self.tree.get_children("nonexistent"), [])
		self.assertIsNone(self.tree.get_parent("nonexistent"))
		
		# These operations should not raise errors
		self.tree.remove_relationship("nonexistent", "child1")
		self.tree.remove_subtree("nonexistent")


	def test_serialization_round_trip(self):
		self.tree.add_relationship("parent1", "child1")
		self.tree.add_relationship("parent1", "child2")
		d = self.tree.to_dict()
		tree2 = BlockTree.from_dict(d)
		self.assertEqual(self.tree, tree2)
		self.assertEqual(tree2.get_parent("child1"), "parent1")
		self.assertEqual(set(tree2.get_children("parent1")), {"child1", "child2"})


	def test_to_dict_structure(self):
		self.tree.add_relationship("a", "b")
		d = self.tree.to_dict()
		self.assertIn("parents", d)
		self.assertIn("children", d)
		self.assertEqual(d["parents"], {"b": "a"})
		self.assertEqual(d["children"], {"a": ["b"]})


	def test_from_dict_empty(self):
		d = {"parents": {}, "children": {}}
		tree = BlockTree.from_dict(d)
		self.assertTrue(tree.is_empty())
		self.assertEqual(tree.parents, {})
		self.assertEqual(tree.children, {})


if __name__ == '__main__':
	unittest.main()
