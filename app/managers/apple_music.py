import os
from ruamel.yaml import YAML
from app.core.job_manager import log, job_manager
from app.managers.notification import NotificationManager
import subprocess
import shutil

class AppleMusicManager:
    """
    Manager for handling Apple Music Downloader configuration and interactions.
    """

    BASE_DIR = os.environ.get('DOWNLOAD_ROOT', '/data/downloads')
    APP_DIR = os.path.join(BASE_DIR, 'Apple Music')

    # Shared state for isolated logging
    _log_history = []
    _running_process = None

    def __init__(self):
        self.yaml = YAML()
        self.yaml.preserve_quotes = True
        self.yaml.indent(mapping=2, sequence=4, offset=2)

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
        if len(cls._log_history) > 200:
            cls._log_history.pop(0)

    @classmethod
    def get_downloader_status(cls):
        running = cls._running_process is not None and cls._running_process.poll() is None
        return {
            'running': running,
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
        Reads the config.yaml file.
        Returns a dict with 'path' and 'data'.
        """
        path = self.find_config_path()
        if not path:
            return {'error': 'Configuration file not found. Please import the repository first.'}

        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = self.yaml.load(f)

            # Convert to pure dict for JSON serialization if needed,
            # but we want to return it to frontend.
            # ruamel objects are dict-like, so jsonify usually handles them,
            # but strictly speaking we might need to cast simple types if frontend creates issues.
            # For now, let's trust jsonify.
            return {
                'path': path,
                'data': data
            }
        except Exception as e:
            log(f"Error reading config: {e}")
            return {'error': f"Failed to read config file: {str(e)}"}

    def update_config(self, updates):
        """
        Updates the config.yaml file with provided key-value pairs.
        Preserves comments and structure.
        """
        path = self.find_config_path()
        if not path:
            return {'error': 'Configuration file not found.'}

        try:
            # Read first to get the CommentedMap object
            with open(path, 'r', encoding='utf-8') as f:
                data = self.yaml.load(f)

            # Apply updates
            for key, value in updates.items():
                if key in data:
                    # Basic type casting if necessary (frontend might send strings for bools)
                    current_val = data[key]
                    if isinstance(current_val, bool) and not isinstance(value, bool):
                        value = str(value).lower() == 'true'
                    elif isinstance(current_val, int) and not isinstance(value, int):
                        try:
                            value = int(value)
                        except:
                            pass # Keep as is if conversion fails

                    data[key] = value

            # Write back
            with open(path, 'w', encoding='utf-8') as f:
                self.yaml.dump(data, f)

            return {'status': 'success', 'message': 'Configuration saved successfully.'}
        except Exception as e:
            log(f"Error saving config: {e}")
            return {'error': f"Failed to save config: {str(e)}"}

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
