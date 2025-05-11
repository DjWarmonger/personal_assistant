import unittest
import asyncio
import os
import sys
import pytest
import pytest_asyncio
from dotenv import load_dotenv

# Update the import path to include the project root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Use direct imports from operations
from operations.notion_client import NotionClient
from operations.asyncClientManager import AsyncClientManager
from operations.index import Index

class TestFavourites(unittest.TestCase):

	def setUp(self):
		self.index = Index(load_from_disk=False, run_on_start=False)
		# Clear any existing favourites
		self.index.cursor.execute('DELETE FROM favourites')
		self.index.db_conn.commit()


	def to_formatted_uuid(self, uuid: str) -> str:
		return self.index.converter.to_formatted_uuid(uuid)


	def test_add_single_favourite(self):

		test_uuid = "123e4567-e89b-12d3-a456-426614174000"
		self.index.add_notion_url_or_uuid_to_favourites(test_uuid, True)
		
		favourites = self.index.get_favourites()
		self.assertEqual(len(favourites), 1)

		favourites = [self.to_formatted_uuid(uuid) for uuid in favourites]
		self.assertEqual(favourites[0], test_uuid)


	def test_remove_single_favourite(self):
		test_uuid = "123e4567-e89b-12d3-a456-426614174000"
		self.index.add_notion_url_or_uuid_to_favourites(test_uuid, True)
		self.index.add_notion_url_or_uuid_to_favourites(test_uuid, False)
		
		favourites = self.index.get_favourites()
		self.assertEqual(len(favourites), 0)


	def test_add_multiple_favourites(self):
		test_uuids = [
			"123e4567-e89b-12d3-a456-426614174000",
			"987fcdeb-43a2-12d3-a456-426614174000"
		]
		for uuid in test_uuids:
			self.index.add_notion_url_or_uuid_to_favourites(uuid, True)
		
		favourites = self.index.get_favourites()
		self.assertEqual(len(favourites), 2)

		favourites = [self.to_formatted_uuid(uuid) for uuid in favourites]
		for uuid in test_uuids:
			self.assertIn(uuid, favourites)


	def test_remove_multiple_favourites(self):
		test_uuids = [
			"123e4567-e89b-12d3-a456-426614174000",
			"987fcdeb-43a2-12d3-a456-426614174000"
		]
		for uuid in test_uuids:
			self.index.add_notion_url_or_uuid_to_favourites(uuid, True)
		for uuid in test_uuids:
			self.index.add_notion_url_or_uuid_to_favourites(uuid, False)
		
		favourites = self.index.get_favourites()
		self.assertEqual(len(favourites), 0)


	def test_get_favourites_limit(self):
		test_uuids = [
			f"123e4567-e89b-12d3-a456-42661417400{i}" 
			for i in range(5)
		]
		for uuid in test_uuids:
			self.index.add_notion_url_or_uuid_to_favourites(uuid, True)
		
		favourites = self.index.get_favourites(count=3)
		self.assertEqual(len(favourites), 3)


	def test_get_favourites_with_names(self):
		test_uuids = [
			f"123e4567-e89b-12d3-a456-42661417400{i}" 
			for i in range(5)
		]
		for uuid in test_uuids:
			self.index.add_notion_url_or_uuid_to_favourites(uuid, True)
		
		# FIXME: This returns int, not uuid
		favourites = self.index.get_favourites(count=10)
		self.assertEqual(len(favourites), 5)

		for favourite in favourites:
			self.assertIn(self.to_formatted_uuid(favourite), test_uuids)


	def tearDown(self):
		self.index.db_conn.close()


if __name__ == '__main__':
	unittest.main()
