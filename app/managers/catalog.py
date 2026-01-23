import json
import os
import uuid
import logging
from datetime import datetime
from app.managers.sync import SyncManager

logger = logging.getLogger(__name__)

class CatalogManager:
    """
    Manages the catalog database.
    Now supports "Dual Path" strategy:
    1. Primary: 'data/catalog.json' (if Sync is enabled)
    2. Fallback: 'catalog.json' (Root)
    """

    def __init__(self):
        self.primary_path = os.path.join(SyncManager.DATA_DIR, "catalog.json")
        self.fallback_path = "catalog.json"

        # Determine active path
        if SyncManager.is_configured():
            self.catalog_path = self.primary_path
        else:
            self.catalog_path = self.fallback_path

        self.catalog = self.load_catalog()

    def reload(self):
        """Re-checks configuration and reloads data (e.g. after Sync Init)."""
        if SyncManager.is_configured():
            self.catalog_path = self.primary_path
        else:
            self.catalog_path = self.fallback_path
        self.catalog = self.load_catalog()

    def load_catalog(self):
        """Loads the catalog from the JSON file."""
        if not os.path.exists(self.catalog_path):
            logger.info(f"Catalog file not found at {self.catalog_path}. Creating new.")
            return []

        try:
            with open(self.catalog_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Sort by created_at desc
                return sorted(data, key=lambda x: x.get('created_at', ''), reverse=True)
        except Exception as e:
            logger.error(f"Failed to load catalog: {e}")
            return []

    def save_catalog(self, trigger_sync=True):
        """Saves the current catalog state to the JSON file."""
        try:
            # Ensure dir exists if using data path
            if self.catalog_path == self.primary_path:
                os.makedirs(os.path.dirname(self.catalog_path), exist_ok=True)

            with open(self.catalog_path, 'w', encoding='utf-8') as f:
                json.dump(self.catalog, f, indent=2, ensure_ascii=False)
            logger.info(f"Catalog saved to {self.catalog_path}")

            # Auto-Push if Configured
            if trigger_sync and SyncManager.is_configured():
                SyncManager.push_data("Auto-update catalog.json")

            return True
        except Exception as e:
            logger.error(f"Failed to save catalog: {e}")
            return False

    def get_all(self):
        return self.catalog

    def get_by_id(self, item_id):
        for item in self.catalog:
            if item.get("id") == item_id:
                return item
        return None

    def delete_entry(self, item_id):
        initial_len = len(self.catalog)
        self.catalog = [x for x in self.catalog if x.get("id") != item_id]
        if len(self.catalog) < initial_len:
            self.save_catalog()
            return True
        return False

    def create_entry(self, title, file_name, file_size, url, category="General", tags=None, is_encrypted=True):
        """
        Creates a new catalog entry dictionary.
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
