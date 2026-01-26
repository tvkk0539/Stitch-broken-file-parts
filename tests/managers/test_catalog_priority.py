import unittest
import os
import shutil
from app.managers.catalog import CatalogManager
from app.managers.sync import SyncManager

class TestCatalogPriority(unittest.TestCase):

    def setUp(self):
        # Use a temporary directory for testing
        self.test_dir = "test_data_priority"
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
        # Item 1: Priority 2 (Necessary)
        self.mgr.add_entry(self.mgr.create_entry(
            title="Necessary Item", file_name="n.zip", file_size=10, url="u1",
            priority=2, tags=["Tag1"]
        ))
        # Item 2: Priority 1 (Normal)
        self.mgr.add_entry(self.mgr.create_entry(
            title="Normal Item", file_name="norm.zip", file_size=10, url="u2",
            priority=1, tags=["Tag1"]
        ))
        # Item 3: Priority 0 (Unnecessary)
        self.mgr.add_entry(self.mgr.create_entry(
            title="Unnecessary Item", file_name="un.zip", file_size=10, url="u3",
            priority=0, tags=["Tag2"]
        ))

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
        SyncManager.DATA_DIR = self.original_data_dir

    def test_filter_priority_necessary(self):
        items = self.mgr.get_all(priority=2)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['title'], "Necessary Item")

    def test_filter_priority_normal(self):
        items = self.mgr.get_all(priority=1)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['title'], "Normal Item")

    def test_filter_priority_unnecessary(self):
        items = self.mgr.get_all(priority=0)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['title'], "Unnecessary Item")

    def test_filter_priority_and_tag(self):
        # Priority 2 AND Tag1 -> Should match Item 1
        items = self.mgr.get_all(priority=2, tags=["Tag1"])
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['title'], "Necessary Item")

        # Priority 0 AND Tag1 -> Should match None (Item 3 is Priority 0 but Tag2)
        items = self.mgr.get_all(priority=0, tags=["Tag1"])
        self.assertEqual(len(items), 0)

    def test_filter_none(self):
        items = self.mgr.get_all(priority=None)
        self.assertEqual(len(items), 3)

if __name__ == '__main__':
    unittest.main()
