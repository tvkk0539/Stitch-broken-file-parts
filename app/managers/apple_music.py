import os
import sqlite3
import json
import threading
from ruamel.yaml import YAML
from app.core.job_manager import log, job_manager
from app.managers.notification import NotificationManager
import subprocess
import shutil

class AppleMusicDB:
    """
    Dedicated SQLite storage for Apple Music Downloader configuration.
    """
    DB_NAME = 'apple_music.db'

    def __init__(self):
        # Store in data/apple_music.db (isolated)
        # We place the DB in 'data' directory (sibling to downloads usually, or inside it if mapped)
        # But per instruction, "data/apple_music.db".
        # Assuming app root 'data' is better for config persistence.
        # Let's use the project root 'data' folder for consistency with catalog.db if possible,
        # but user asked for "separate".

        # We will put it in the same base 'data' directory where 'catalog.db' usually lives if not synced.
        # However, to be safe and simple, we'll put it in the standard 'data' volume.

        self.db_dir = 'data'
        if not os.path.exists(self.db_dir):
            os.makedirs(self.db_dir, exist_ok=True)

        self.db_path = os.path.join(self.db_dir, self.DB_NAME)
        self._init_db()

    def _get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        try:
            with self._get_conn() as conn:
                # Config Table
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS config (
                        key TEXT PRIMARY KEY,
                        value TEXT
                    )
                """)

                # Queue Table
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS download_queue (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        url TEXT NOT NULL,
                        args TEXT, -- JSON
                        status TEXT DEFAULT 'pending', -- pending, processing, completed, failed
                        error TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                conn.commit()
        except Exception as e:
            log(f"AM-DB Init Error: {e}")

    def get_all(self):
        """Returns all settings as a dictionary."""
        try:
            with self._get_conn() as conn:
                rows = conn.execute("SELECT key, value FROM config").fetchall()
                return {row['key']: row['value'] for row in rows}
        except Exception as e:
            log(f"AM-DB Get All Error: {e}")
            return {}

    def get(self, key):
        try:
            with self._get_conn() as conn:
                row = conn.execute("SELECT value FROM config WHERE key = ?", (key,)).fetchone()
                if row:
                    return row['value']
        except Exception as e:
            log(f"AM-DB Get Error: {e}")
        return None

    def set(self, key, value):
        """Sets a single value. Value is converted to string."""
        try:
            with self._get_conn() as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)",
                    (key, str(value))
                )
                conn.commit()
        except Exception as e:
            log(f"AM-DB Set Error: {e}")

    def bulk_update(self, data_dict):
        """Updates multiple keys."""
        try:
            with self._get_conn() as conn:
                for k, v in data_dict.items():
                    conn.execute(
                        "INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)",
                        (k, str(v))
                    )
                conn.commit()
        except Exception as e:
            log(f"AM-DB Bulk Update Error: {e}")

    def is_empty(self):
        try:
            with self._get_conn() as conn:
                count = conn.execute("SELECT count(*) FROM config").fetchone()[0]
                return count == 0
        except:
            return True

    # --- Queue DB Operations ---

    def add_queue_item(self, url, args):
        try:
            with self._get_conn() as conn:
                conn.execute(
                    "INSERT INTO download_queue (url, args, status) VALUES (?, ?, 'pending')",
                    (url, json.dumps(args))
                )
                conn.commit()
            return True
        except Exception as e:
            log(f"AM-Queue Add Error: {e}")
            return False

    def get_queue_items(self):
        try:
            items = []
            with self._get_conn() as conn:
                rows = conn.execute("SELECT * FROM download_queue ORDER BY created_at ASC").fetchall()
                for row in rows:
                    items.append(dict(row))
            return items
        except Exception as e:
            log(f"AM-Queue Get Error: {e}")
            return []

    def update_queue_status(self, item_id, status, error=None):
        try:
            with self._get_conn() as conn:
                conn.execute(
                    "UPDATE download_queue SET status = ?, error = ? WHERE id = ?",
                    (status, error, item_id)
                )
                conn.commit()
        except Exception as e:
            log(f"AM-Queue Update Error: {e}")

    def delete_queue_item(self, item_id):
        try:
            with self._get_conn() as conn:
                conn.execute("DELETE FROM download_queue WHERE id = ?", (item_id,))
                conn.commit()
            return True
        except Exception as e:
            log(f"AM-Queue Delete Error: {e}")
            return False

    def get_next_pending(self):
        try:
            with self._get_conn() as conn:
                row = conn.execute("SELECT * FROM download_queue WHERE status = 'pending' ORDER BY id ASC LIMIT 1").fetchone()
                if row:
                    return dict(row)
        except Exception as e:
            log(f"AM-Queue Next Error: {e}")
        return None

class AppleMusicManager:
    """
    Manager for handling Apple Music Downloader configuration and interactions.
    """

    BASE_DIR = os.environ.get('DOWNLOAD_ROOT', '/data/downloads')
    APP_DIR = os.path.join(BASE_DIR, 'Apple Music')

    # Shared state for isolated logging
    _log_history = []
    _running_process = None

    # Queue Control
    _queue_active = False
    _stop_requested = False

    def __init__(self):
        self.yaml = YAML()
        self.yaml.preserve_quotes = True
        self.yaml.indent(mapping=2, sequence=4, offset=2)

        self.db = AppleMusicDB()
        self._ensure_synced()

    def _ensure_synced(self):
        """
        Ensures DB and File are in sync on startup.
        Priority:
        1. If DB is empty -> Import from File (Initial Migration).
        2. If DB has data -> We assume DB is truth (Lazy Sync is handled on save, but we can verify here).
        """
        if self.db.is_empty():
            log("AM-Manager: DB is empty. Attempting import from config.yaml...")
            self._sync_from_yaml_to_db()

    def _sync_from_yaml_to_db(self):
        """Reads config.yaml (if exists) and populates DB."""
        path = self.find_config_path()
        if not path or not os.path.exists(path):
            return

        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = self.yaml.load(f)

            if data:
                # Convert complex types if necessary, but simple dict is expected
                flat_data = {}
                for k, v in data.items():
                    # Check for non-scalar types if any
                    flat_data[k] = v

                self.db.bulk_update(flat_data)
                log(f"AM-Manager: Imported {len(flat_data)} keys from {path}")
        except Exception as e:
            log(f"AM-Manager Import Error: {e}")

    def _sync_from_db_to_yaml(self):
        """
        Writes DB values to config.yaml.
        Crucial: Preserves comments by reading the file first.
        """
        path = self.find_config_path()
        if not path:
            return {'error': 'Config file not found on disk.'}

        try:
            # 1. Read File (Template)
            with open(path, 'r', encoding='utf-8') as f:
                yaml_data = self.yaml.load(f)

            # 2. Get DB Values
            db_values = self.db.get_all()

            # 3. Update Yaml Object (Preserving Types)
            for key, str_val in db_values.items():
                if key in yaml_data:
                    current_val = yaml_data[key]

                    # Type Inference to preserve YAML types
                    # Because DB stores everything as TEXT
                    new_val = str_val

                    if isinstance(current_val, bool):
                        new_val = str(str_val).lower() == 'true'
                    elif isinstance(current_val, int):
                        try:
                            new_val = int(str_val)
                        except:
                            pass # Fallback to string
                    elif current_val is None:
                        # If yaml had null, try to guess from string
                        if str_val.lower() == 'true': new_val = True
                        elif str_val.lower() == 'false': new_val = False
                        elif str_val.isdigit(): new_val = int(str_val)

                    yaml_data[key] = new_val
                else:
                    # New key (not in file)
                    # We add it, but it won't have comments.
                    # Try to infer type
                    if str_val.lower() == 'true': yaml_data[key] = True
                    elif str_val.lower() == 'false': yaml_data[key] = False
                    elif str_val.isdigit(): yaml_data[key] = int(str_val)
                    else: yaml_data[key] = str_val

            # 4. Write Back
            with open(path, 'w', encoding='utf-8') as f:
                self.yaml.dump(yaml_data, f)

            log(f"AM-Manager: Synced DB to {path}")
            return {'status': 'success'}

        except Exception as e:
            log(f"AM-Manager Sync Export Error: {e}")
            return {'error': str(e)}

    @classmethod
    def _append_log(cls, message):
        # Progress Bar Debouncing
        # If new message is progress, and last message was progress, replace it.
        is_progress = message.startswith("Downloading...") or message.startswith("Decrypting...")

        if is_progress and cls._log_history:
            last = cls._log_history[-1]
            if last.startswith("Downloading...") or last.startswith("Decrypting..."):
                cls._log_history[-1] = message
                return

        cls._log_history.append(message)
        if len(cls._log_history) > 1000:
            cls._log_history.pop(0)

    @classmethod
    def get_downloader_status(cls):
        running = cls._running_process is not None and cls._running_process.poll() is None
        return {
            'running': running,
            'queue_active': cls._queue_active,
            'logs': cls._log_history
        }

    def check_dependencies(self):
        """Checks if external tools (Go, mp4decrypt, ffmpeg) are available."""
        return {
            'go': shutil.which('go') is not None,
            'mp4decrypt': shutil.which('mp4decrypt') is not None,
            'ffmpeg': shutil.which('ffmpeg') is not None,
            'mp4box': shutil.which('MP4Box') is not None
        }

    def find_install_path(self):
        """
        Finds the directory containing main.go.
        """
        if not os.path.exists(self.APP_DIR):
            return None

        # 1. Check default
        default_dir = os.path.join(self.APP_DIR, 'apple-music-downloader')
        if os.path.exists(os.path.join(default_dir, 'main.go')):
            return default_dir

        # 2. Scan subdirs
        try:
            with os.scandir(self.APP_DIR) as it:
                for entry in it:
                    if entry.is_dir():
                        candidate = os.path.join(entry.path, 'main.go')
                        if os.path.exists(candidate):
                            return entry.path
        except: pass
        return None

    def find_config_path(self):
        """
        Intelligently searches for config.yaml in the Apple Music directory.
        """
        install_dir = self.find_install_path()
        if install_dir:
            return os.path.join(install_dir, 'config.yaml')
        return None

    def get_config(self):
        """
        Returns configuration from the Database.
        """
        path = self.find_config_path()
        if not path:
            return {'error': 'Configuration file not found. Please import the repository first.'}

        try:
            # Return DB values
            # We return them as a dict. The frontend expects 'data'.
            # Note: DB values are strings. The frontend handles string->bool/int
            # rendering via schema types, but sending proper types is nicer.
            # However, since we store as text, we send text.
            # The UI schema (apple_music.js) handles 'bool' type fields by checking 'true'/'false'.

            data = self.db.get_all()

            # Simple Type Casting for standard UI expectations (optional but good)
            # Actually, let's keep it raw strings to be safe with DB storage,
            # and let the frontend schema handle display logic (checked=value=='true').
            # But wait, frontend apple_music.js: input.checked = field.value === true;
            # So we SHOULD convert "true" to True for the frontend.

            clean_data = {}
            for k, v in data.items():
                if v.lower() == 'true': clean_data[k] = True
                elif v.lower() == 'false': clean_data[k] = False
                elif v.isdigit(): clean_data[k] = int(v)
                else: clean_data[k] = v

            return {
                'path': path,
                'data': clean_data
            }
        except Exception as e:
            log(f"Error reading config from DB: {e}")
            return {'error': f"Failed to read config: {str(e)}"}

    def update_config(self, updates):
        """
        Updates the Database then Syncs to config.yaml.
        """
        try:
            # 1. Update Database
            self.db.bulk_update(updates)

            # 2. Sync to File (Preserving comments)
            result = self._sync_from_db_to_yaml()

            if 'error' in result:
                return result

            return {'status': 'success', 'message': 'Configuration saved to DB and Disk.'}

        except Exception as e:
            log(f"Error saving config: {e}")
            return {'error': f"Failed to save config: {str(e)}"}

    def reload_config_from_disk(self):
        """
        Manually triggers a sync from Disk -> DB.
        Useful if the user manually edited config.yaml.
        """
        try:
            log("AM-Manager: Manual reload requested.")
            self._sync_from_yaml_to_db()
            return self.get_config()
        except Exception as e:
            log(f"Error reloading config: {e}")
            return {'error': f"Failed to reload config: {str(e)}"}

    # --- Queue Management Logic ---

    def add_to_queue(self, url, args):
        if self.db.add_queue_item(url, args):
            return {'status': 'success', 'message': 'Added to queue'}
        return {'error': 'Failed to add to queue'}

    def get_queue(self):
        return self.db.get_queue_items()

    def remove_from_queue(self, item_id):
        if self.db.delete_queue_item(item_id):
            return {'status': 'success'}
        return {'error': 'Failed to delete'}

    def stop_queue(self):
        """Signals the queue processor to stop after current job."""
        if AppleMusicManager._queue_active:
            AppleMusicManager._stop_requested = True
            log("AM-Queue: Stopping after current job...")
            return {'status': 'stopping'}
        return {'status': 'not_running'}

    def start_queue(self):
        """Starts the queue processor if not running."""
        if AppleMusicManager._queue_active:
            return {'status': 'already_running'}

        AppleMusicManager._queue_active = True
        AppleMusicManager._stop_requested = False

        # Run in background via JobManager to not block request
        # But wait, JobManager runs TASKS. The Queue Processor is a Daemon-like loop.
        # Ideally, we submit a "Queue Processor" job to JobManager.
        job_manager.add_job(
            "Apple Music Queue Processor",
            self._process_queue_loop,
            args=()
        )
        return {'status': 'started'}

    def _process_queue_loop(self):
        """
        Worker loop that picks pending items and runs them.
        """
        log("AM-Queue: Processor Started")

        while True:
            if AppleMusicManager._stop_requested:
                log("AM-Queue: Stop requested. Exiting loop.")
                break

            item = self.db.get_next_pending()
            if not item:
                log("AM-Queue: No pending items. Finished.")
                break

            # Process Item
            log(f"AM-Queue: Processing Item #{item['id']} - {item['url']}")
            self.db.update_queue_status(item['id'], 'processing')

            try:
                # Parse args
                args = json.loads(item['args']) if item['args'] else {}

                # Execute Download (Synchronous within this thread)
                # We reuse run_download_job logic but need it to raise exception on failure
                # to mark status correctly.
                success = self._run_download_sync(item['url'], args)

                if success:
                    self.db.update_queue_status(item['id'], 'completed')
                else:
                    self.db.update_queue_status(item['id'], 'failed', 'Download process returned error')

            except Exception as e:
                log(f"AM-Queue Error processing #{item['id']}: {e}")
                self.db.update_queue_status(item['id'], 'failed', str(e))

        AppleMusicManager._queue_active = False
        AppleMusicManager._stop_requested = False
        log("AM-Queue: Processor Stopped")

    def _run_download_sync(self, url, args):
        """
        Internal helper to run download synchronously and return Success (bool).
        Similar to run_download_job but returns status instead of just logging.
        """
        work_dir = self.find_install_path()
        if not work_dir:
            raise Exception("Downloader not found")

        cmd = ['go', 'run', 'main.go']
        if args:
            for k, v in args.items():
                if v is True: cmd.append(f"--{k}")
                elif v:
                    cmd.append(f"--{k}")
                    cmd.append(str(v))
        cmd.append(url)

        process = subprocess.Popen(
            cmd,
            cwd=work_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            universal_newlines=True,
            env={**os.environ, 'PATH': os.environ.get('PATH', '')}
        )

        job_manager.set_current_process(process)
        AppleMusicManager._running_process = process

        for line in process.stdout:
            line = line.strip()
            if line:
                is_prog = line.startswith("Downloading...") or line.startswith("Decrypting...")
                if not is_prog: log(f"[AM-Queue] {line}")
                AppleMusicManager._append_log(line)
                if "Downloading" in line:
                    job_manager.update_job_details({'action': f"Queue Item: {line}"})

        process.wait()
        AppleMusicManager._running_process = None

        return process.returncode == 0

    @staticmethod
    def run_download_job(url, args=None):
        """
        Executes the Apple Music Downloader via 'go run main.go'.
        """
        manager = AppleMusicManager()
        work_dir = manager.find_install_path()

        if not work_dir:
            log("Apple Music Downloader not found.")
            job_manager.update_job_details({'error': 'Downloader not found. Please install via Setup tab.'})
            return

        log(f"Starting Apple Music Download: {url}")
        job_manager.update_job_details({
            'action': 'Initializing Downloader...',
            'url': url
        })

        # Construct Command
        # go run main.go [args] url
        cmd = ['go', 'run', 'main.go']

        if args:
            # Add flags like --atmos, --aac, --select
            for k, v in args.items():
                if v is True: # bool flag
                    cmd.append(f"--{k}")
                elif v: # value flag
                    cmd.append(f"--{k}")
                    cmd.append(str(v))

        cmd.append(url)

        try:
            if job_manager.is_cancelled(): return

            process = subprocess.Popen(
                cmd,
                cwd=work_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL, # Prevent hanging on prompts
                universal_newlines=True,
                env={**os.environ, 'PATH': os.environ.get('PATH', '')}
            )
            job_manager.set_current_process(process)
            AppleMusicManager._running_process = process # Track for status polling

            for line in process.stdout:
                line = line.strip()
                if line:
                    # Filter System Log: Don't spam "Downloading..."
                    is_progress = line.startswith("Downloading...") or line.startswith("Decrypting...")
                    if not is_progress:
                        log(f"[AM-DL] {line}")

                    # Update Console (Debounced)
                    AppleMusicManager._append_log(line)

                    # Update Job UI status
                    if "Downloading" in line:
                        job_manager.update_job_details({'action': line})

            process.wait()
            AppleMusicManager._running_process = None # Clear when done

            if process.returncode == 0:
                log("Download Complete.")
                NotificationManager.send_notification("✅ ParFix: Apple Music Download Complete")
            else:
                if job_manager.is_cancelled():
                    log("Download Cancelled")
                else:
                    log(f"Download failed (Code {process.returncode})")
                    job_manager.update_job_details({'error': f"Failed (Code {process.returncode})"})
                    NotificationManager.send_notification("❌ ParFix: Apple Music Download Failed")

        except Exception as e:
            log(f"Download Error: {e}")
            job_manager.update_job_details({'error': str(e)})
