import json
import os
import uuid
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class CatalogManager:
    """
    Manages the 'catalog.json' file which serves as the local database
    for the Bridge Architecture.
    """

    def __init__(self, catalog_path="catalog.json"):
        self.catalog_path = catalog_path
        self.catalog = self.load_catalog()

    def load_catalog(self):
        """Loads the catalog from the JSON file."""
        if not os.path.exists(self.catalog_path):
            logger.info(f"Catalog file not found at {self.catalog_path}. Creating new.")
            return []

        try:
            with open(self.catalog_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load catalog: {e}")
            return []

    def save_catalog(self):
        """Saves the current catalog state to the JSON file."""
        try:
            with open(self.catalog_path, 'w', encoding='utf-8') as f:
                json.dump(self.catalog, f, indent=2, ensure_ascii=False)
            logger.info(f"Catalog saved to {self.catalog_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save catalog: {e}")
            return False

    def create_entry(self, title, file_name, file_size, url, category="General", tags=None, is_encrypted=True):
        """
        Creates a new catalog entry dictionary.

        Args:
            title (str): The display title (e.g. "Avengers").
            file_name (str): The actual filename (e.g. "Data_99.rar").
            file_size (int): Size in bytes.
            url (str): The GitHub Release download URL.
            category (str): Category (Movies, Apps, etc).
            tags (list): List of string tags.
            is_encrypted (bool): Whether the file is password protected/obfuscated.

        Returns:
            dict: The new entry object.
        """
        if tags is None:
            tags = []

        entry = {
            "id": str(uuid.uuid4()),
            "title": title,
            "category": category,
            "file_name": file_name,
            "size_bytes": file_size,
            "size_human": self._human_readable_size(file_size),
            "release_url": url,
            "created_at": datetime.utcnow().isoformat() + "Z",
            "tags": tags,
            "is_encrypted": is_encrypted
        }
        return entry

    def add_entry(self, entry):
        """Adds an entry to the catalog and saves."""
        # Prepend to list so newest is first
        self.catalog.insert(0, entry)
        return self.save_catalog()

    def _human_readable_size(self, size, decimal_places=2):
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.{decimal_places}f} {unit}"
            size /= 1024.0
        return f"{size:.{decimal_places}f} PB"

    # -------------------------------------------------------------------------
    # Bridge / Sync Logic (Placeholder for Phase 2 integration)
    # -------------------------------------------------------------------------
    def sync_to_github(self, repo_name, token):
        """
        Future implementation:
        1. Clone/Pull the Private Bridge Repo to a temp folder.
        2. Copy local catalog.json to that folder.
        3. Git add, commit, push.
        """
        pass
