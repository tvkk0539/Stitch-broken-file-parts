import os
import subprocess
import threading
import queue
import time
import requests
import zipfile
import shutil
from app.core.job_manager import log

class AppleMusicWrapperManager:
    """
    Manages the Apple Music Decryption Wrapper binary.
    Handles installation, execution, and interactive I/O (2FA).
    """

    BASE_DIR = os.environ.get('DOWNLOAD_ROOT', '/data/downloads')
    APP_DIR = os.path.join(BASE_DIR, 'Apple Music')
    WRAPPER_DIR = os.path.join(APP_DIR, 'wrapper')
    # Use the linux binary name inside the extracted folder
    # Based on user info: "Wrapper.x86_64" inside "wrapper" folder after rename
    BINARY_NAME = 'wrapper'
    DOWNLOAD_URL = "https://github.com/zhaarey/wrapper/releases/download/linux.V2/Wrapper.x86_64.zip"

    def __init__(self):
        self.process = None
        self.log_queue = queue.Queue(maxsize=100)
        self.log_history = []
        self.stop_event = threading.Event()
        self.io_thread = None

    def _log(self, message):
        """Internal logging to memory buffer for UI consumption."""
        ts = time.strftime("%H:%M:%S")
        entry = f"[{ts}] {message}"
        self.log_history.append(entry)
        if len(self.log_history) > 100:
            self.log_history.pop(0)
        log(f"[AM Wrapper] {message}")

    # --- Installation ---

    def is_installed(self):
        # We look for the executable
        # If user renamed folder to 'wrapper', and inside is 'wrapper' executable (we'll rename it during install)
        exe_path = os.path.join(self.WRAPPER_DIR, self.BINARY_NAME)
        return os.path.exists(exe_path)

    def install(self, custom_url=None):
        target_url = custom_url if custom_url else self.DOWNLOAD_URL
        self._log(f"Starting installation from {target_url}...")
        os.makedirs(self.APP_DIR, exist_ok=True)

        zip_path = os.path.join(self.APP_DIR, 'wrapper_temp.zip')

        try:
            # 1. Download
            self._log(f"Downloading...")
            with requests.get(target_url, stream=True) as r:
                r.raise_for_status()
                with open(zip_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)

            # 2. Extract
            self._log("Extracting...")
            extract_temp = os.path.join(self.APP_DIR, 'wrapper_extract_temp')
            if os.path.exists(extract_temp):
                shutil.rmtree(extract_temp)

            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_temp)

            # 3. Locate and Move
            # The zip likely contains a single file or a folder.
            # User said: "rename that folder to completely as wrapper"
            # But the URL is a zip of a single binary usually? Or a folder?
            # Let's inspect what we got.
            # Assuming zip content is simple. We want final path: .../Apple Music/wrapper/wrapper

            if os.path.exists(self.WRAPPER_DIR):
                shutil.rmtree(self.WRAPPER_DIR)
            os.makedirs(self.WRAPPER_DIR)

            # Find the binary in extract_temp
            found_binary = None
            for root, dirs, files in os.walk(extract_temp):
                for file in files:
                    if "wrapper" in file.lower():
                        found_binary = os.path.join(root, file)
                        break

            if found_binary:
                target_path = os.path.join(self.WRAPPER_DIR, self.BINARY_NAME)
                shutil.move(found_binary, target_path)
                os.chmod(target_path, 0o755) # Make executable
                self._log("Installation successful.")
            else:
                raise Exception("Could not locate wrapper binary in downloaded archive")

        except Exception as e:
            self._log(f"Installation failed: {e}")
            raise e
        finally:
            # Cleanup
            if os.path.exists(zip_path): os.remove(zip_path)
            if os.path.exists(extract_temp): shutil.rmtree(extract_temp)

    # --- Execution ---

    def start(self, username, password):
        if self.process and self.process.poll() is None:
            return {'error': 'Wrapper is already running'}

        if not self.is_installed():
            return {'error': 'Wrapper not installed'}

        exe_path = os.path.join(self.WRAPPER_DIR, self.BINARY_NAME)

        # Args: ./wrapper -L username:password -H 0.0.0.0
        # -H 0.0.0.0 is crucial for docker container to listen on all interfaces
        cmd = [exe_path, '-L', f"{username}:{password}", '-H', '0.0.0.0']

        try:
            # Start process with pipes
            self.process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, # Merge stderr into stdout
                text=True, # Text mode for easier reading
                bufsize=1, # Line buffered
                cwd=self.WRAPPER_DIR
            )

            self._log(f"Wrapper started with PID {self.process.pid}")

            # Start monitoring thread
            self.stop_event.clear()
            self.io_thread = threading.Thread(target=self._monitor_output)
            self.io_thread.daemon = True
            self.io_thread.start()

            return {'status': 'started', 'pid': self.process.pid}
        except Exception as e:
            self._log(f"Failed to start wrapper: {e}")
            return {'error': str(e)}

    def stop(self):
        if self.process:
            self._log("Stopping wrapper...")
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
            self._log("Wrapper stopped.")
            self.process = None
        return {'status': 'stopped'}

    def send_input(self, text):
        """Writes text to the process stdin (e.g., 2FA code)."""
        if not self.process or self.process.poll() is not None:
            return {'error': 'Wrapper is not running'}

        try:
            self._log(f"Sending Input: {text}")
            # Ensure newline
            if not text.endswith('\n'):
                text += '\n'

            self.process.stdin.write(text)
            self.process.stdin.flush()
            return {'status': 'sent'}
        except Exception as e:
            self._log(f"Error sending input: {e}")
            return {'error': str(e)}

    def get_status(self):
        running = self.process is not None and self.process.poll() is None
        return {
            'installed': self.is_installed(),
            'running': running,
            'pid': self.process.pid if running else None,
            'logs': self.log_history[-50:] # Return last 50 lines
        }

    def _monitor_output(self):
        """Background thread to read stdout and populate logs."""
        if not self.process: return

        try:
            for line in iter(self.process.stdout.readline, ''):
                if self.stop_event.is_set(): break
                if line:
                    clean_line = line.strip()
                    if clean_line:
                        self._log(clean_line)
        except Exception as e:
            self._log(f"Monitor error: {e}")
        finally:
            # If loop exits, process likely ended
            if self.process:
                ret = self.process.poll()
                if ret is not None:
                    self._log(f"Process exited with code {ret}")
