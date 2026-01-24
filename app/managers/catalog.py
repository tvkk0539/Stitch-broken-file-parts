import json
import os
import uuid
import logging
from datetime import datetime
from app.managers.sync import SyncManager
from app.managers.github_tool import GitHubManager # Needed for fetch logic
from werkzeug.utils import secure_filename

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

    def create_entry(self, title, file_name, file_size, url, category="General", tags=None, is_encrypted=True, assets=None, image=None):
        """
        Creates a new catalog entry dictionary.
        Assets: List of {name, size, url}
        Image: Path to local image (relative to data/ or static/)
        """
        if tags is None:
            tags = []
        if assets is None:
            assets = []

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
            "is_encrypted": is_encrypted,
            "assets": assets,
            "image": image # Path to local image
        }
        return entry

    def add_entry(self, entry):
        """Adds an entry to the catalog and saves."""
        # Prepend to list so newest is first
        self.catalog.insert(0, entry)
        return self.save_catalog()

    def fetch_github_metadata(self, url):
        """
        Fetches release details from a GitHub Release URL.
        Returns: { title, total_size, assets_list, release_tag }
        """
        try:
            # 1. Parse URL to get Repo and Tag
            # Format: https://github.com/user/repo/releases/tag/v1.0.0
            if "github.com" not in url or "releases" not in url:
                return {'error': 'Invalid GitHub Release URL'}

            parts = url.replace("https://github.com/", "").split('/')
            owner, repo = parts[0], parts[1]

            # Find tag
            tag = None
            if "tag" in parts:
                tag_idx = parts.index("tag")
                if len(parts) > tag_idx + 1:
                    tag = parts[tag_idx + 1]
            elif "download" in parts:
                 # It's a file link? Try to infer release from context or fail
                 return {'error': 'Please provide the Release page URL (ends with /tag/version)'}

            # 2. Use GitHubManager to fetch releases
            repo_url = f"https://github.com/{owner}/{repo}"
            releases = GitHubManager.get_releases(repo_url)

            if isinstance(releases, dict) and 'error' in releases:
                return releases

            # 3. Find the matching release
            target_release = None
            if tag:
                for r in releases:
                    if r['tag'] == tag:
                        target_release = r
                        break
            else:
                # If no tag in URL, maybe latest? Assuming user gave releases page?
                # Safer to require tag or pick first if user gave base releases url
                if releases:
                    target_release = releases[0]

            if not target_release:
                return {'error': 'Release not found'}

            # 4. Process Assets
            total_size = 0
            assets_out = []

            for asset in target_release['assets']:
                size = asset['size']
                total_size += size
                assets_out.append({
                    'name': asset['name'],
                    'size': size,
                    'url': asset['download_url']
                })

            return {
                'status': 'success',
                'title': f"{repo} - {target_release['name'] or target_release['tag']}",
                'total_size': total_size,
                'file_count': len(assets_out),
                'assets': assets_out,
                'tag': target_release['tag']
            }

        except Exception as e:
            logger.error(f"Fetch metadata error: {e}")
            return {'error': str(e)}

    def save_image(self, file_obj):
        """
        Saves an uploaded image to the data/assets/images directory.
        Returns the relative path to store in catalog.
        """
        try:
            # Determine base dir: 'data/assets/images' if sync enabled, else 'static/images/catalog' ?
            # User wants Sync enabled assets.

            if SyncManager.is_configured():
                base_dir = os.path.join(SyncManager.DATA_DIR, "assets", "images")
            else:
                # Fallback to local data folder (ignored by git)
                base_dir = os.path.join("data", "assets", "images")

            os.makedirs(base_dir, exist_ok=True)

            # Generate safe name
            ext = os.path.splitext(file_obj.filename)[1].lower()
            if ext not in ['.jpg', '.jpeg', '.png', '.webp']:
                ext = '.jpg'

            filename = f"{uuid.uuid4()}{ext}"
            file_path = os.path.join(base_dir, filename)

            file_obj.save(file_path)

            # Trigger Sync if configured (to back up the image)
            if SyncManager.is_configured():
                SyncManager.push_data(f"Added image asset: {filename}")

            # Return relative path for API serving
            # We will serve via /api/catalog/image/<filename> which maps to this dir
            return filename

        except Exception as e:
            logger.error(f"Save image error: {e}")
            return None

    def get_image_path(self, filename):
        """Resolves the absolute path for an image filename."""
        if SyncManager.is_configured():
            return os.path.join(SyncManager.DATA_DIR, "assets", "images", filename)
        else:
            return os.path.join("data", "assets", "images", filename)

    def _human_readable_size(self, size, decimal_places=2):
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.{decimal_places}f} {unit}"
            size /= 1024.0
        return f"{size:.{decimal_places}f} PB"
