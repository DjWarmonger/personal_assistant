import unittest
import asyncio
import os
import sys
from typing import List, Union

# Update the import path to include the project root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Use direct imports from operations
from operations.notion.notion_client import NotionClient
from operations.notion.asyncClientManager import AsyncClientManager
from operations.blocks.index import Index
from tz_common import CustomUUID

class TestFavourites(unittest.TestCase):

	def setUp(self):
		self.index = Index(load_from_disk=False, run_on_start=False)
		# Clear any existing favourites
		self.index.cursor.execute('DELETE FROM favourites')
		self.index.db_conn.commit()
		self.loop = asyncio.new_event_loop()
		asyncio.set_event_loop(self.loop)
		self.notion_client = self.loop.run_until_complete(NotionClient(load_from_disk=False, run_on_start=False).__aenter__())

	def tearDown(self):
		self.loop.run_until_complete(self.notion_client.__aexit__(None, None, None))
		self.loop.close()
		if os.path.exists(self.index.db_path):
			os.remove(self.index.db_path)

	def to_formatted_uuid(self, uuid: Union[str, CustomUUID]) -> str:
		if isinstance(uuid, CustomUUID):
			return uuid.to_formatted()
		elif isinstance(uuid, str):
			# Assuming if it's a string, it might need to be converted to CustomUUID first
			# This path might need adjustment based on how strings are handled upstream
			return CustomUUID.from_string(uuid).to_formatted()
		raise TypeError(f"Expected str or CustomUUID, got {type(uuid)}")

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


if __name__ == '__main__':
	unittest.main()
