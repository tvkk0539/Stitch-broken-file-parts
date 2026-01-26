import unittest
import os
import shutil
import sqlite3
import json
from app.managers.catalog import CatalogManager
from app.managers.sync import SyncManager

class TestCatalogMultiTags(unittest.TestCase):

    def setUp(self):
        # Use a temporary directory for testing
        self.test_dir = "test_data_multitag"
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
        os.makedirs(self.test_dir)

        # Monkey patch SyncManager path to use test_dir
        self.original_data_dir = SyncManager.DATA_DIR
        SyncManager.DATA_DIR = self.test_dir

        self.mgr = CatalogManager()
        self.mgr.fallback_dir = self.test_dir
        self.mgr.reload()

        # Populate with test data
        self.create_test_items()

    def create_test_items(self):
        # Item 1: "Action", "4K"
        self.mgr.add_entry(self.mgr.create_entry(
            title="Item 1", file_name="i1.zip", file_size=10, url="u1",
            tags=["Action", "4K"]
        ))
        # Item 2: "Action", "HD"
        self.mgr.add_entry(self.mgr.create_entry(
            title="Item 2", file_name="i2.zip", file_size=10, url="u2",
            tags=["Action", "HD"]
        ))
        # Item 3: "Comedy", "4K", "Family"
        self.mgr.add_entry(self.mgr.create_entry(
            title="Item 3", file_name="i3.zip", file_size=10, url="u3",
            tags=["Comedy", "4K", "Family"]
        ))
        # Item 4: "Action", "4K", "Thriller"
        self.mgr.add_entry(self.mgr.create_entry(
            title="Item 4", file_name="i4.zip", file_size=10, url="u4",
            tags=["Action", "4K", "Thriller"]
        ))

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
        SyncManager.DATA_DIR = self.original_data_dir

    def test_filter_single_tag(self):
        # Should match Item 1, 2, 4
        items = self.mgr.get_all(tags=["Action"])
        self.assertEqual(len(items), 3)
        titles = sorted([i['title'] for i in items])
        self.assertEqual(titles, ["Item 1", "Item 2", "Item 4"])

    def test_filter_multiple_tags_intersection(self):
        # "Action" AND "4K" -> Should match Item 1 and Item 4
        items = self.mgr.get_all(tags=["Action", "4K"])
        self.assertEqual(len(items), 2)
        titles = sorted([i['title'] for i in items])
        self.assertEqual(titles, ["Item 1", "Item 4"])

    def test_filter_multiple_tags_intersection_empty(self):
        # "Action" AND "Comedy" -> Should match None
        items = self.mgr.get_all(tags=["Action", "Comedy"])
        self.assertEqual(len(items), 0)

    def test_filter_three_tags(self):
        # "Action", "4K", "Thriller" -> Should match Item 4
        items = self.mgr.get_all(tags=["Action", "4K", "Thriller"])
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['title'], "Item 4")

    def test_filter_string_input(self):
        # Should handle comma-separated string
        items = self.mgr.get_all(tags="Action, 4K")
        self.assertEqual(len(items), 2)
        titles = sorted([i['title'] for i in items])
        self.assertEqual(titles, ["Item 1", "Item 4"])

if __name__ == '__main__':
    unittest.main()
