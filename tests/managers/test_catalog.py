import unittest
import os
import shutil
import sqlite3
import json
from app.managers.catalog import CatalogManager
from app.managers.sync import SyncManager

class TestCatalogManager(unittest.TestCase):

    def setUp(self):
        # Use a temporary directory for testing
        self.test_dir = "test_data"
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
        os.makedirs(self.test_dir)

        # Monkey patch SyncManager path to use test_dir
        self.original_data_dir = SyncManager.DATA_DIR
        SyncManager.DATA_DIR = self.test_dir

        self.mgr = CatalogManager()
        self.mgr.fallback_dir = self.test_dir
        self.mgr.reload()

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
        SyncManager.DATA_DIR = self.original_data_dir

    def test_create_entry_with_description(self):
        entry = self.mgr.create_entry(
            title="Test Item",
            file_name="test.zip",
            file_size=100,
            url="http://example.com",
            description="Base64EncodedTreeData"
        )
        self.assertEqual(entry['description'], "Base64EncodedTreeData")

        self.mgr.add_entry(entry)

        # Verify in DB
        saved = self.mgr.get_by_id(entry['id'])
        self.assertEqual(saved['description'], "Base64EncodedTreeData")

    def test_update_entry_description(self):
        entry = self.mgr.create_entry("Old Title", "old.zip", 10, "url")
        self.mgr.add_entry(entry)

        self.mgr.update_entry(entry['id'], {
            "title": "New Title",
            "description": "Updated Description"
        })

        updated = self.mgr.get_by_id(entry['id'])
        self.assertEqual(updated['title'], "New Title")
        self.assertEqual(updated['description'], "Updated Description")

    def test_json_export_on_add(self):
        # Configure SyncManager to be "configured" by creating .git
        os.makedirs(os.path.join(self.test_dir, ".git"))

        # Add entry (should trigger sync -> export)
        entry = self.mgr.create_entry("Backup Test", "bkp.zip", 10, "url")
        self.mgr.add_entry(entry)

        # Check if catalog.json exists
        json_path = os.path.join(self.test_dir, "catalog.json")
        self.assertTrue(os.path.exists(json_path), "catalog.json should be created")

        with open(json_path, 'r') as f:
            data = json.load(f)
            self.assertEqual(len(data), 1)
            self.assertEqual(data[0]['title'], "Backup Test")

if __name__ == '__main__':
    unittest.main()
