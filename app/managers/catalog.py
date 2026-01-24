import sqlite3
import os
import uuid
import json
import logging
from datetime import datetime
from app.managers.sync import SyncManager
from app.managers.github_tool import GitHubManager
from werkzeug.utils import secure_filename
from PIL import Image

logger = logging.getLogger(__name__)

class CatalogManager:
    """
    Manages the catalog database using SQLite for scalability.
    Supports "Dual Path" strategy via SyncManager.
    """

    def __init__(self):
        # Paths
        self.primary_dir = SyncManager.DATA_DIR
        self.fallback_dir = "."

        self.db_name = "catalog.db"
        self.json_name = "catalog.json" # Legacy support

        self.db_path = self._resolve_path(self.db_name)
        self.json_path = self._resolve_path(self.json_name)

        self._init_db()
        self._migrate_json_to_sqlite()

    def _resolve_path(self, filename):
        """Returns the path in 'data/' if configured, else root."""
        if SyncManager.is_configured():
            path = os.path.join(self.primary_dir, filename)
            # Ensure dir exists
            os.makedirs(os.path.dirname(path), exist_ok=True)
            return path
        return os.path.join(self.fallback_dir, filename)

    def _get_conn(self):
        """Returns a sqlite connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Creates the items table if it doesn't exist."""
        try:
            with self._get_conn() as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS items (
                        id TEXT PRIMARY KEY,
                        title TEXT NOT NULL,
                        category TEXT,
                        file_name TEXT,
                        size_bytes INTEGER,
                        size_human TEXT,
                        release_url TEXT,
                        created_at TEXT,
                        tags TEXT,       -- JSON list
                        is_encrypted INTEGER,
                        image TEXT,
                        assets TEXT,     -- JSON list of dicts
                        priority INTEGER DEFAULT 1 -- 2=High, 1=Normal, 0=Low
                    )
                """)
                conn.commit()

            # Check for migration of priority column
            self._migrate_priority_column()

        except Exception as e:
            logger.error(f"DB Init Error: {e}")

    def _migrate_priority_column(self):
        """Adds priority column if missing."""
        try:
            with self._get_conn() as conn:
                cursor = conn.execute("PRAGMA table_info(items)")
                columns = [info[1] for info in cursor.fetchall()]
                if 'priority' not in columns:
                    logger.info("Migrating DB: Adding priority column...")
                    conn.execute("ALTER TABLE items ADD COLUMN priority INTEGER DEFAULT 1")
                    conn.commit()
        except Exception as e:
            logger.error(f"Priority Migration Error: {e}")

    def _migrate_json_to_sqlite(self):
        """Imports legacy catalog.json into catalog.db if db is empty."""
        try:
            # Check if JSON exists
            if not os.path.exists(self.json_path):
                return

            # Check if DB is empty
            with self._get_conn() as conn:
                count = conn.execute("SELECT count(*) FROM items").fetchone()[0]
                if count > 0:
                    return # DB already populated

            logger.info("Migrating JSON catalog to SQLite...")

            with open(self.json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            with self._get_conn() as conn:
                for item in data:
                    conn.execute("""
                        INSERT INTO items (id, title, category, file_name, size_bytes, size_human,
                                           release_url, created_at, tags, is_encrypted, image, assets)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        item.get('id'),
                        item.get('title'),
                        item.get('category'),
                        item.get('file_name'),
                        item.get('size_bytes'),
                        item.get('size_human'),
                        item.get('release_url'),
                        item.get('created_at'),
                        json.dumps(item.get('tags', [])),
                        1 if item.get('is_encrypted') else 0,
                        item.get('image'),
                        json.dumps(item.get('assets', []))
                    ))
                conn.commit()

            # Rename JSON to .bak to avoid confusion
            os.rename(self.json_path, self.json_path + ".bak")
            logger.info("Migration complete. JSON renamed to .bak")

            # Trigger Sync
            self.trigger_sync("Migrated JSON to SQLite")

        except Exception as e:
            logger.error(f"Migration Error: {e}")

    def reload(self):
        """Re-initializes paths (e.g. after Sync Init)."""
        self.db_path = self._resolve_path(self.db_name)
        self.json_path = self._resolve_path(self.json_name)
        self._init_db()
        self._migrate_json_to_sqlite()

    def get_all(self, page=1, limit=50, search=None, tag=None):
        """
        Retrieves paginated and filtered items.
        Sorted by Priority DESC, then CreatedAt DESC.
        """
        offset = (page - 1) * limit
        query = "SELECT * FROM items WHERE 1=1"
        params = []

        if search:
            query += " AND (lower(title) LIKE ? OR lower(category) LIKE ?)"
            term = f"%{search.lower()}%"
            params.extend([term, term])

        if tag:
            # Simple tag search in JSON string
            query += " AND tags LIKE ?"
            params.append(f"%{tag}%")

        # Sort: High Priority first (2), then Normal (1), then Low (0), then Date
        query += " ORDER BY priority DESC, created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        items = []
        try:
            with self._get_conn() as conn:
                rows = conn.execute(query, params).fetchall()
                for row in rows:
                    items.append(self._row_to_dict(row))
        except Exception as e:
            logger.error(f"Get All Error: {e}")

        return items

    def _row_to_dict(self, row):
        """Converts a SQLite Row to a Dictionary."""
        d = dict(row)
        # Parse JSON fields
        if d.get('tags'): d['tags'] = json.loads(d['tags'])
        else: d['tags'] = []

        if d.get('assets'): d['assets'] = json.loads(d['assets'])
        else: d['assets'] = []

        d['is_encrypted'] = bool(d['is_encrypted'])
        return d

    def get_by_id(self, item_id):
        try:
            with self._get_conn() as conn:
                row = conn.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
                if row:
                    return self._row_to_dict(row)
        except Exception as e:
            logger.error(f"Get ID Error: {e}")
        return None

    def create_entry(self, title, file_name, file_size, url, category="General", tags=None, is_encrypted=True, assets=None, image=None, priority=1):
        if tags is None: tags = []
        if assets is None: assets = []

        return {
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
            "image": image,
            "priority": priority
        }

    def add_entry(self, entry):
        """Inserts an entry into the DB."""
        try:
            with self._get_conn() as conn:
                conn.execute("""
                    INSERT INTO items (id, title, category, file_name, size_bytes, size_human,
                                       release_url, created_at, tags, is_encrypted, image, assets, priority)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    entry['id'],
                    entry['title'],
                    entry['category'],
                    entry['file_name'],
                    entry['size_bytes'],
                    entry['size_human'],
                    entry['release_url'],
                    entry['created_at'],
                    json.dumps(entry['tags']),
                    1 if entry['is_encrypted'] else 0,
                    entry['image'],
                    json.dumps(entry['assets']),
                    entry.get('priority', 1)
                ))
                conn.commit()

            self.trigger_sync(f"Added item: {entry['title']}")
            return True
        except Exception as e:
            logger.error(f"Add Entry Error: {e}")
            return False

    def get_all_tags(self):
        """Returns a list of all unique tags used in the library."""
        try:
            with self._get_conn() as conn:
                rows = conn.execute("SELECT tags FROM items").fetchall()

            all_tags = set()
            for row in rows:
                if row['tags']:
                    try:
                        tag_list = json.loads(row['tags'])
                        for t in tag_list:
                            if t.strip(): all_tags.add(t.strip())
                    except: pass

            return sorted(list(all_tags))
        except Exception as e:
            logger.error(f"Get Tags Error: {e}")
            return []

    def update_entry(self, item_id, data):
        """
        Updates an existing entry.
        """
        try:
            with self._get_conn() as conn:
                current = conn.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
                if not current:
                    return {'error': 'Item not found'}

                current = self._row_to_dict(current)

                new_image = data.get('image')
                old_image = current.get('image')
                final_image = old_image

                if 'image' in data:
                    final_image = new_image
                    if old_image and new_image != old_image:
                        self._delete_image_file(old_image)

                conn.execute("""
                    UPDATE items SET
                        title = ?,
                        category = ?,
                        tags = ?,
                        image = ?,
                        release_url = ?,
                        assets = ?,
                        priority = ?
                    WHERE id = ?
                """, (
                    data.get('title', current['title']),
                    data.get('category', current['category']),
                    json.dumps(data.get('tags', current['tags'])),
                    final_image,
                    data.get('release_url', current['release_url']),
                    json.dumps(data.get('assets', current['assets'])),
                    int(data.get('priority', current.get('priority', 1))),
                    item_id
                ))
                conn.commit()

            self.trigger_sync(f"Updated item: {item_id}")
            return {'status': 'success'}

        except Exception as e:
            logger.error(f"Update Entry Error: {e}")
            return {'error': str(e)}

    def delete_entry(self, item_id):
        try:
            with self._get_conn() as conn:
                # 1. Get image to delete first
                row = conn.execute("SELECT image FROM items WHERE id = ?", (item_id,)).fetchone()
                image_to_delete = row['image'] if row else None

                # 2. Delete DB Row
                cursor = conn.execute("DELETE FROM items WHERE id = ?", (item_id,))
                conn.commit()

                if cursor.rowcount > 0:
                    # 3. Delete image if row deleted successfully
                    if image_to_delete:
                        self._delete_image_file(image_to_delete)

                    self.trigger_sync(f"Deleted item {item_id}")
                    return True
        except Exception as e:
            logger.error(f"Delete Error: {e}")
        return False

    def trigger_sync(self, message):
        """Calls SyncManager to push the DB file."""
        if SyncManager.is_configured():
            # Ensure we are syncing the DB file
            ok, msg = SyncManager.push_data(message)
            if ok:
                logger.info(f"Sync Success: {msg}")
            else:
                logger.error(f"Sync Failed: {msg}")

    def fetch_github_metadata(self, url):
        """Proxy to GitHubManager to fetch release details."""
        try:
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

            repo_url = f"https://github.com/{owner}/{repo}"
            releases = GitHubManager.get_releases(repo_url)

            if isinstance(releases, dict) and 'error' in releases:
                return releases

            target_release = None
            if tag:
                for r in releases:
                    if r['tag'] == tag:
                        target_release = r
                        break
            else:
                if releases: target_release = releases[0]

            if not target_release:
                return {'error': 'Release not found'}

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

    def save_image(self, file_obj, optimize=True, is_local_path=False):
        """
        Saves image to data/assets/images and returns filename.
        file_obj: FileStorage object OR path string (if is_local_path=True)
        """
        try:
            if SyncManager.is_configured():
                base_dir = os.path.join(SyncManager.DATA_DIR, "assets", "images")
            else:
                base_dir = os.path.join("data", "assets", "images")

            os.makedirs(base_dir, exist_ok=True)

            # Determine extension and input source
            if is_local_path:
                original_filename = os.path.basename(file_obj)
                source_path = file_obj
            else:
                original_filename = file_obj.filename

            ext = os.path.splitext(original_filename)[1].lower()
            if optimize:
                ext = '.jpg'
            elif ext not in ['.jpg', '.jpeg', '.png', '.webp']:
                ext = '.jpg'

            filename = f"{uuid.uuid4()}{ext}"
            file_path = os.path.join(base_dir, filename)

            if optimize:
                img = Image.open(source_path if is_local_path else file_obj)
                if img.mode in ("RGBA", "P"): img = img.convert("RGB")

                max_width = 800
                if img.width > max_width:
                    ratio = max_width / float(img.width)
                    new_height = int((float(img.height) * float(ratio)))
                    img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)

                img.save(file_path, "JPEG", quality=90)
            else:
                if is_local_path:
                    import shutil
                    shutil.copy2(source_path, file_path)
                else:
                    file_obj.save(file_path)

            if SyncManager.is_configured():
                SyncManager.push_data(f"Added image asset: {filename}")

            return filename
        except Exception as e:
            logger.error(f"Save image error: {e}")
            return None

    def _delete_image_file(self, filename):
        """Deletes the physical image file."""
        try:
            path = self.get_image_path(filename)
            if os.path.exists(path):
                os.remove(path)
        except Exception as e:
            logger.error(f"Failed to delete image {filename}: {e}")

    def get_image_path(self, filename):
        if SyncManager.is_configured():
            return os.path.join(SyncManager.DATA_DIR, "assets", "images", filename)
        return os.path.join("data", "assets", "images", filename)

    def _human_readable_size(self, size, decimal_places=2):
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.{decimal_places}f} {unit}"
            size /= 1024.0
        return f"{size:.{decimal_places}f} PB"
