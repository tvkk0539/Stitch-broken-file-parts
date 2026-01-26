import os
from ruamel.yaml import YAML
from app.core.job_manager import log
import subprocess
import shutil

class AppleMusicManager:
    """
    Manager for handling Apple Music Downloader configuration and interactions.
    """

    BASE_DIR = os.environ.get('DOWNLOAD_ROOT', '/data/downloads')
    APP_DIR = os.path.join(BASE_DIR, 'Apple Music')

    def __init__(self):
        self.yaml = YAML()
        self.yaml.preserve_quotes = True
        self.yaml.indent(mapping=2, sequence=4, offset=2)

    def check_dependencies(self):
        """Checks if external tools (Go, mp4decrypt, ffmpeg) are available."""
        return {
            'go': shutil.which('go') is not None,
            'mp4decrypt': shutil.which('mp4decrypt') is not None,
            'ffmpeg': shutil.which('ffmpeg') is not None,
            'mp4box': shutil.which('MP4Box') is not None
        }

    def find_config_path(self):
        """
        Intelligently searches for config.yaml in the Apple Music directory.
        Prioritizes 'apple-music-downloader' folder, then scans others.
        """
        if not os.path.exists(self.APP_DIR):
            return None

        # 1. Check default expected path
        default_path = os.path.join(self.APP_DIR, 'apple-music-downloader', 'config.yaml')
        if os.path.exists(default_path):
            return default_path

        # 2. Scan subdirectories
        try:
            with os.scandir(self.APP_DIR) as it:
                for entry in it:
                    if entry.is_dir():
                        candidate = os.path.join(entry.path, 'config.yaml')
                        if os.path.exists(candidate):
                            return candidate
        except Exception as e:
            log(f"Error scanning for Apple Music config: {e}")

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
