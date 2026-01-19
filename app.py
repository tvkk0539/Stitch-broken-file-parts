import os
import time
import subprocess
import threading
import queue
import json
import requests
import shutil
from flask import Flask, render_template, jsonify, request, Response

app = Flask(__name__)

# Configuration
# Default download directory. In Docker, this should be mapped to the host's download folder.
DOWNLOAD_ROOT = os.environ.get('DOWNLOAD_ROOT', '/data/downloads')
# Support external config mapping or default location
CONFIG_FILE = os.environ.get('CONFIG_FILE', '/app/config.json')

# Global queue for log streaming
log_queue = queue.Queue()

# Job Queue System (Advanced)
class JobManager:
    def __init__(self):
        self.queue = []
        self.current_job = None
        self.current_process = None # For killing subprocesses
        self.lock = threading.Lock()
        self.queue_event = threading.Event()

    def add_job(self, name, target, args):
        with self.lock:
            # Simple ID generation
            job_id = str(int(time.time() * 1000))
            self.queue.append({
                'id': job_id,
                'name': name,
                'target': target,
                'args': args
            })
            self.queue_event.set()
            return job_id

    def cancel_job(self, job_id):
        with self.lock:
            # Check if pending
            for i, job in enumerate(self.queue):
                if job['id'] == job_id:
                    del self.queue[i]
                    log(f"Cancelled pending job: {job['name']}")
                    return True

            # Check if running
            if self.current_job and self.current_job['id'] == job_id:
                log(f"Cancelling running job: {self.current_job['name']}")
                self.kill_current_process()
                return True
        return False

    def register_process(self, process):
        self.current_process = process

    def kill_current_process(self):
        if self.current_process:
            try:
                log("Terminating process...")
                self.current_process.terminate()
                # Give it a moment, then force kill if needed?
                # Keeping it simple for now.
            except Exception as e:
                log(f"Failed to kill process: {e}")

    def get_status(self):
        with self.lock:
            return {
                'current': {
                    'id': self.current_job['id'],
                    'name': self.current_job['name']
                } if self.current_job else None,
                'queue': [
                    {'id': j['id'], 'name': j['name']} for j in self.queue
                ]
            }

    def get_next_job(self):
        with self.lock:
            if self.queue:
                return self.queue.pop(0)
            else:
                self.queue_event.clear()
                return None

job_manager = JobManager()

def log(message):
    """Adds a message to the log queue."""
    timestamp = time.strftime("%H:%M:%S")
    formatted_message = f"[{timestamp}] {message}"
    print(formatted_message)  # Also print to stdout for container logs
    log_queue.put(formatted_message)

def worker():
    """Background worker that processes jobs from the queue."""
    while True:
        job = job_manager.get_next_job()

        if not job:
            # Wait for new jobs
            job_manager.queue_event.wait()
            continue

        with job_manager.lock:
            job_manager.current_job = job
            job_manager.current_process = None # Reset process tracker

        job_name = job.get('name', 'Unknown Job')
        log(f"Starting Queued Job: {job_name}")

        target = job.get('target')
        args = job.get('args', ())

        try:
            target(*args)
        except Exception as e:
            log(f"Job {job_name} Failed: {e}")
            import traceback
            log(traceback.format_exc())
        finally:
            log(f"Finished Job: {job_name}")
            with job_manager.lock:
                job_manager.current_job = None
                job_manager.current_process = None

# Start the worker thread
threading.Thread(target=worker, daemon=True).start()

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f)

class NotificationManager:
    @staticmethod
    def send_notification(message):
        config = load_config()

        # Discord
        discord_url = config.get('discord_webhook')
        if discord_url:
            try:
                requests.post(discord_url, json={"content": message})
            except Exception as e:
                log(f"Failed to send Discord notification: {e}")

        # Telegram
        tg_token = config.get('telegram_token')
        tg_chat = config.get('telegram_chat_id')
        if tg_token and tg_chat:
            try:
                url = f"https://api.telegram.org/bot{tg_token}/sendMessage"
                requests.post(url, json={"chat_id": tg_chat, "text": message})
            except Exception as e:
                log(f"Failed to send Telegram notification: {e}")

class RcloneManager:
    @staticmethod
    def list_remotes():
        try:
            # rclone listremotes
            # Note: rclone.conf must be mounted at /config/rclone/rclone.conf usually or ~/.config/rclone/rclone.conf
            # We assume user mounts config to /root/.config/rclone/rclone.conf or we set env var
            # RCLONE_CONFIG is standard env var.

            result = subprocess.run(['rclone', 'listremotes'], capture_output=True, text=True)
            if result.returncode != 0:
                return []

            remotes = [r.strip().rstrip(':') for r in result.stdout.split('\n') if r.strip()]
            return remotes
        except FileNotFoundError:
            return []

    @staticmethod
    def run_upload(source_paths, remote, upload_path, transfers=4):
        # source_paths is a list of file OR folder paths
        log(f"Starting Rclone Upload to {remote}:{upload_path} (Parallel: {transfers})")

        if not source_paths:
            return True

        # Separate directories and files
        dirs = []
        files = []
        for p in source_paths:
            if os.path.isdir(p):
                dirs.append(p)
            else:
                files.append(p)

        failed = False

        # Process Directories (One by one, recursive copy)
        for d in dirs:
            folder_name = os.path.basename(d)
            # If upload_path is empty, use folder_name. If set, append folder_name.
            target_path = os.path.join(upload_path, folder_name) if upload_path else folder_name

            log(f"Uploading directory: {d} -> {remote}:{target_path}")

            cmd = ['rclone', 'copy', d, f"{remote}:{target_path}",
                   '--transfers', str(transfers),
                   '--stats', '2s',
                   '-v']

            if not RcloneManager._execute_rclone(cmd):
                failed = True

        # Process Files (Batch by parent directory for efficiency)
        if files:
            from collections import defaultdict
            grouped_files = defaultdict(list)

            for f in files:
                parent = os.path.dirname(f)
                grouped_files[parent].append(os.path.basename(f))

            for parent_dir, filenames in grouped_files.items():
                log(f"Processing batch of {len(filenames)} files from {parent_dir}...")

                cmd = ['rclone', 'copy', parent_dir, f"{remote}:{upload_path}",
                       '--transfers', str(transfers),
                       '--stats', '2s',
                       '-v']

                for name in filenames:
                    cmd.append('--include')
                    cmd.append(name)

                if not RcloneManager._execute_rclone(cmd):
                    failed = True

        if not failed:
            log("All uploads completed successfully.")
            return True
        return False

    @staticmethod
    def _execute_rclone(cmd):
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True
            )

            # Register for cancellation
            if job_manager.current_job:
                job_manager.register_process(process)

            for line in process.stdout:
                line = line.strip()
                if not line: continue

                if "error" in line.lower() or "failed" in line.lower():
                    log(f"[RCLONE ERROR] {line}")
                elif "Transferred:" in line:
                     log(f"[UPLOAD] {line}")
                elif "100%" in line:
                     log(f"[UPLOAD] {line}")

            process.wait()
            if process.returncode != 0:
                log(f"Rclone failed with code {process.returncode}")
                return False
            return True

        except Exception as e:
            log(f"Rclone Execution Error: {e}")
            return False

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/list')
def list_files():
    """Lists directories and files in the given path (safe browsing)."""
    req_path = request.args.get('path', '')

    # Construct absolute path
    abs_path = os.path.join(DOWNLOAD_ROOT, req_path).rstrip('/')

    # Security check: Ensure we don't traverse above DOWNLOAD_ROOT
    if not os.path.abspath(abs_path).startswith(os.path.abspath(DOWNLOAD_ROOT)):
        return jsonify({'error': 'Access denied'}), 403

    if not os.path.exists(abs_path):
        return jsonify({'error': 'Path not found'}), 404

    items = []
    try:
        with os.scandir(abs_path) as it:
            for entry in it:
                items.append({
                    'name': entry.name,
                    'is_dir': entry.is_dir(),
                    'path': os.path.join(req_path, entry.name)
                })
    except PermissionError:
        return jsonify({'error': 'Permission denied'}), 403

    # Sort: Directories first, then files
    items.sort(key=lambda x: (not x['is_dir'], x['name'].lower()))

    return jsonify({
        'current_path': req_path,
        'parent_path': os.path.dirname(req_path) if req_path else None,
        'items': items
    })

@app.route('/api/logs')
def stream_logs():
    """Streams logs to the client using Server-Sent Events (SSE)."""
    def generate():
        while True:
            try:
                # Wait for new log message
                message = log_queue.get(timeout=20)
                yield f"data: {message}\n\n"
            except queue.Empty:
                # Send a keep-alive ping to prevent connection timeout
                yield ": keep-alive\n\n"

    return Response(generate(), mimetype='text/event-stream')

@app.route('/api/repair', methods=['POST'])
def trigger_repair():
    """Triggers the repair process for a specific directory."""
    data = request.json
    target_path = data.get('path')

    if not target_path:
        return jsonify({'error': 'No path provided'}), 400

    abs_path = os.path.join(DOWNLOAD_ROOT, target_path)

    # Security check
    if not os.path.abspath(abs_path).startswith(os.path.abspath(DOWNLOAD_ROOT)):
        return jsonify({'error': 'Access denied'}), 403

    if not os.path.exists(abs_path):
        return jsonify({'error': 'Path not found'}), 404

    # Handle file selection (convert to parent directory)
    work_dir = abs_path
    target_par2 = None

    if not os.path.isdir(abs_path):
        work_dir = os.path.dirname(abs_path)
        # If user selected a par2 file specifically, pass it as target
        if abs_path.lower().endswith('.par2'):
            target_par2 = os.path.basename(abs_path)

    # Add to Job Queue
    job_queue.put({
        'name': f"Repair {target_path}",
        'target': RepairManager.run_repair_job,
        'args': (work_dir, target_par2)
    })

    return jsonify({'status': 'queued', 'message': f'Repair job queued for {target_path}'})

@app.route('/api/archive', methods=['POST'])
def trigger_archive():
    """Triggers the creation of a multi-part archive."""
    data = request.json
    target_path = data.get('path')
    name = data.get('name')
    split_size = data.get('split_size', '1024M') # Default 1GB
    password = data.get('password')
    fmt = data.get('format', 'rar') # rar or 7z
    create_par2 = data.get('create_par2', True) # Default True

    # Upload Options
    upload = data.get('upload', False)
    remote = data.get('remote')
    upload_path = data.get('upload_path', '')

    if not target_path or not name:
        return jsonify({'error': 'Path and Name are required'}), 400

    abs_path = os.path.join(DOWNLOAD_ROOT, target_path)

    # Security check
    if not os.path.abspath(abs_path).startswith(os.path.abspath(DOWNLOAD_ROOT)):
        return jsonify({'error': 'Access denied'}), 403

    if not os.path.exists(abs_path):
        return jsonify({'error': 'Path not found'}), 404

    # Add to Job Queue
    job_queue.put({
        'name': f"Pack {name}",
        'target': ArchiveManager.run_archive_job,
        'args': (abs_path, name, split_size, password, fmt, create_par2, upload, remote, upload_path)
    })

    return jsonify({'status': 'queued', 'message': f'Archiving queued for {name}'})

@app.route('/api/settings', methods=['GET', 'POST'])
def settings():
    if request.method == 'POST':
        data = request.json
        save_config(data)
        return jsonify({'status': 'saved'})
    else:
        return jsonify(load_config())

@app.route('/api/remotes')
def get_remotes():
    return jsonify(RcloneManager.list_remotes())

@app.route('/api/queue', methods=['GET'])
def get_queue_status():
    return jsonify(job_manager.get_status())

@app.route('/api/queue/cancel/<job_id>', methods=['POST'])
def cancel_job_endpoint(job_id):
    success = job_manager.cancel_job(job_id)
    if success:
        return jsonify({'status': 'cancelled'})
    else:
        return jsonify({'error': 'Job not found'}), 404

@app.route('/api/upload', methods=['POST'])
def trigger_manual_upload():
    data = request.json
    target_paths = data.get('paths') # Expecting list
    remote = data.get('remote')
    upload_path = data.get('upload_path', '')

    if not target_paths or not remote:
        return jsonify({'error': 'Paths and Remote are required'}), 400

    abs_paths = []
    for p in target_paths:
        abs_p = os.path.join(DOWNLOAD_ROOT, p)
        # Security check
        if not os.path.abspath(abs_p).startswith(os.path.abspath(DOWNLOAD_ROOT)):
            continue
        abs_paths.append(abs_p)

    if not abs_paths:
        return jsonify({'error': 'No valid paths found'}), 400

    transfers = data.get('transfers', 4) # Default concurrency
    try:
        transfers = int(transfers)
    except:
        transfers = 4

    # Add to Job Queue
    job_queue.put({
        'name': f"Upload to {remote}",
        'target': RcloneManager.run_upload,
        'args': (abs_paths, remote, upload_path, transfers)
    })
    return jsonify({'status': 'queued'})

@app.route('/api/extract', methods=['POST'])
def trigger_extract():
    data = request.json
    target_path = data.get('path')
    method = data.get('method', 'unrar')
    password = data.get('password')

    if not target_path:
        return jsonify({'error': 'Path required'}), 400

    abs_path = os.path.join(DOWNLOAD_ROOT, target_path)
    if not os.path.exists(abs_path):
        return jsonify({'error': 'Path not found'}), 404

    # Security check
    if not os.path.abspath(abs_path).startswith(os.path.abspath(DOWNLOAD_ROOT)):
        return jsonify({'error': 'Access denied'}), 403

    # Add to Job Queue
    job_queue.put({
        'name': f"Extract {os.path.basename(target_path)}",
        'target': ExtractManager.run_extract_job,
        'args': (abs_path, method, password)
    })
    return jsonify({'status': 'queued'})

@app.route('/api/rename', methods=['POST'])
def rename_item():
    data = request.json
    target_path = data.get('path')
    new_name = data.get('new_name')

    if not target_path or not new_name:
        return jsonify({'error': 'Path and new name required'}), 400

    abs_path = os.path.join(DOWNLOAD_ROOT, target_path)
    parent_dir = os.path.dirname(abs_path)
    new_abs_path = os.path.join(parent_dir, new_name)

    # Security Checks
    if not os.path.abspath(abs_path).startswith(os.path.abspath(DOWNLOAD_ROOT)):
        return jsonify({'error': 'Access denied'}), 403
    if not os.path.abspath(new_abs_path).startswith(os.path.abspath(DOWNLOAD_ROOT)):
        return jsonify({'error': 'Access denied (New Path)'}), 403

    if not os.path.exists(abs_path):
        return jsonify({'error': 'Item not found'}), 404

    if os.path.exists(new_abs_path):
        return jsonify({'error': 'Destination already exists'}), 400

    try:
        os.rename(abs_path, new_abs_path)
        log(f"Renamed {target_path} -> {os.path.join(os.path.dirname(target_path), new_name)}")
        return jsonify({'status': 'renamed'})
    except Exception as e:
        log(f"Rename Error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/delete', methods=['POST'])
def trigger_delete():
    data = request.json
    target_paths = data.get('paths')

    if not target_paths:
        return jsonify({'error': 'No paths provided'}), 400

    success_count = 0
    errors = []

    for p in target_paths:
        abs_path = os.path.join(DOWNLOAD_ROOT, p)

        # Security Check
        if not os.path.abspath(abs_path).startswith(os.path.abspath(DOWNLOAD_ROOT)):
            errors.append(f"Access denied: {p}")
            continue

        if not os.path.exists(abs_path):
            errors.append(f"Not found: {p}")
            continue

        try:
            if os.path.isdir(abs_path):
                shutil.rmtree(abs_path)
            else:
                os.remove(abs_path)
            success_count += 1
            log(f"Deleted: {p}")
        except Exception as e:
            errors.append(f"Failed to delete {p}: {str(e)}")
            log(f"Delete Error for {p}: {str(e)}")

    return jsonify({
        'status': 'completed',
        'deleted': success_count,
        'errors': errors
    })

@app.route('/api/mkdir', methods=['POST'])
def make_directory():
    data = request.json
    parent_path = data.get('path', '')
    name = data.get('name')

    if not name:
        return jsonify({'error': 'Folder name required'}), 400

    abs_parent = os.path.join(DOWNLOAD_ROOT, parent_path)
    new_dir_path = os.path.join(abs_parent, name)

    # Security Check
    if not os.path.abspath(new_dir_path).startswith(os.path.abspath(DOWNLOAD_ROOT)):
        return jsonify({'error': 'Access denied'}), 403

    try:
        os.makedirs(new_dir_path, exist_ok=True)
        log(f"Created directory: {os.path.join(parent_path, name)}")
        return jsonify({'status': 'created'})
    except Exception as e:
        log(f"Mkdir Error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/move', methods=['POST'])
def move_items():
    data = request.json
    paths = data.get('paths', [])
    dest_path = data.get('destination', '')

    if not paths:
        return jsonify({'error': 'No items selected'}), 400

    abs_dest = os.path.join(DOWNLOAD_ROOT, dest_path)

    # Ensure destination exists
    if not os.path.exists(abs_dest):
        return jsonify({'error': 'Destination folder does not exist'}), 404

    # Security Check (Destination)
    if not os.path.abspath(abs_dest).startswith(os.path.abspath(DOWNLOAD_ROOT)):
        return jsonify({'error': 'Access denied (Destination)'}), 403

    success_count = 0
    errors = []

    for p in paths:
        abs_src = os.path.join(DOWNLOAD_ROOT, p)

        # Security Check (Source)
        if not os.path.abspath(abs_src).startswith(os.path.abspath(DOWNLOAD_ROOT)):
            errors.append(f"Access denied: {p}")
            continue

        if not os.path.exists(abs_src):
            errors.append(f"Not found: {p}")
            continue

        try:
            shutil.move(abs_src, abs_dest)
            success_count += 1
            log(f"Moved {p} to {dest_path}")
        except Exception as e:
            errors.append(f"Failed to move {p}: {str(e)}")
            log(f"Move Error for {p}: {str(e)}")

    return jsonify({
        'status': 'completed',
        'moved': success_count,
        'errors': errors
    })

@app.route('/api/copy', methods=['POST'])
def copy_items():
    data = request.json
    paths = data.get('paths', [])
    dest_path = data.get('destination', '')

    if not paths:
        return jsonify({'error': 'No items selected'}), 400

    abs_dest = os.path.join(DOWNLOAD_ROOT, dest_path)

    # Ensure destination exists
    if not os.path.exists(abs_dest):
        return jsonify({'error': 'Destination folder does not exist'}), 404

    # Security Check (Destination)
    if not os.path.abspath(abs_dest).startswith(os.path.abspath(DOWNLOAD_ROOT)):
        return jsonify({'error': 'Access denied (Destination)'}), 403

    success_count = 0
    errors = []

    for p in paths:
        abs_src = os.path.join(DOWNLOAD_ROOT, p)

        # Security Check (Source)
        if not os.path.abspath(abs_src).startswith(os.path.abspath(DOWNLOAD_ROOT)):
            errors.append(f"Access denied: {p}")
            continue

        if not os.path.exists(abs_src):
            errors.append(f"Not found: {p}")
            continue

        try:
            # Determine destination path (keep filename)
            basename = os.path.basename(abs_src)
            final_dest = os.path.join(abs_dest, basename)

            if os.path.isdir(abs_src):
                shutil.copytree(abs_src, final_dest, dirs_exist_ok=True)
            else:
                shutil.copy2(abs_src, final_dest)

            success_count += 1
            log(f"Copied {p} to {dest_path}")
        except Exception as e:
            errors.append(f"Failed to copy {p}: {str(e)}")
            log(f"Copy Error for {p}: {str(e)}")

    return jsonify({
        'status': 'completed',
        'copied': success_count,
        'errors': errors
    })

class ArchiveManager:
    @staticmethod
    def run_archive_job(source_path, archive_name, split_size, password, fmt='rar', create_par2=True, upload=False, remote=None, upload_path=''):
        parent_dir = os.path.dirname(source_path)
        base_name = os.path.basename(source_path)

        # Extension handling
        ext = '.rar' if fmt == 'rar' else '.7z'
        if not archive_name.endswith(ext):
            archive_name += ext

        log(f"Starting Archive Job: Packing '{base_name}' into '{archive_name}'")
        log(f"Format: {fmt}, Split: {split_size}, PAR2: {create_par2}, Upload: {upload}")

        cmd = []

        if fmt == 'rar':
            # rar a -m0 -v{size} -hp{password} -ep1 "{archive_name}" "{source_path}"
            cmd = ['rar', 'a', '-m0', f'-v{split_size}', '-ep1']
            if password:
                cmd.append(f'-hp{password}')
            cmd.append(archive_name)
            cmd.append(source_path)
        else:
            # 7z a -v{size} -mx0 -p{password} "{archive_name}" "{source_path}"
            # 7z split sizes need 'm' (e.g. 1024m), ensure case matching if needed.
            # Convert 1024M -> 1024m for 7z usually just needs numbers or kmg.
            # 7z syntax: -v1g or -v1024m

            size_arg = split_size.lower().replace('m', 'm').replace('g', 'g')
            cmd = ['7z', 'a', f'-v{size_arg}', '-mx0']
            if password:
                cmd.append(f'-p{password}')
                cmd.append('-mhe=on') # Encrypt headers

            cmd.append(archive_name)
            cmd.append(source_path)

        try:
            # --- PHASE 1: ARCHIVING ---
            log(f"Running {fmt.upper()} command...")

            process = subprocess.Popen(
                cmd,
                cwd=parent_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True
            )

            for line in process.stdout:
                line = line.strip()
                if line:
                    if "%" in line or "Creating" in line or "Done" in line:
                         log(f"[{fmt.upper()}] {line}")
                    elif "Error" in line:
                         log(f"[{fmt.upper()} ERROR] {line}")

            process.wait()

            if process.returncode != 0:
                log(f"Archiving failed with code {process.returncode}")
                NotificationManager.send_notification(f"❌ ParFix: Archiving Failed for {archive_name}")
                return

            log("Archive created successfully.")

            # Collect generated files for potential upload
            generated_files = []

            # --- PHASE 2: PAR2 GENERATION ---
            if create_par2:
                log("Starting PAR2 Recovery File Generation...")

                par2_base = archive_name + ".par2"

                target_pattern = ""
                if fmt == 'rar':
                    # Check if split happened
                    if os.path.exists(os.path.join(parent_dir, archive_name.replace('.rar', '.part01.rar'))) or \
                       os.path.exists(os.path.join(parent_dir, archive_name.replace('.rar', '.part001.rar'))):
                         target_pattern = archive_name.replace('.rar', '.part*.rar')
                    else:
                         target_pattern = archive_name
                else:
                    target_pattern = archive_name + ".*"

                # Manual match is safer for Python
                import glob

                search_pattern = os.path.join(parent_dir, target_pattern)
                files_to_protect = glob.glob(search_pattern)

                # If 7z, we might also have the .7z file itself if not split?
                if not files_to_protect and os.path.exists(os.path.join(parent_dir, archive_name)):
                    files_to_protect = [os.path.join(parent_dir, archive_name)]

                if not files_to_protect:
                    log("Warning: Could not find archive files to protect with PAR2.")
                else:
                    files_to_protect.sort()
                    generated_files.extend(files_to_protect)

                    par2_cmd = ['par2', 'c', '-r10']
                    par2_cmd.append(par2_base)
                    par2_cmd.extend([os.path.basename(f) for f in files_to_protect])

                    log(f"Creating PAR2 for {len(files_to_protect)} files...")

                    p2_process = subprocess.Popen(
                        par2_cmd,
                        cwd=parent_dir,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        universal_newlines=True
                    )

                    for line in p2_process.stdout:
                        if "Compute" in line or "Constructing" in line:
                             log(f"[PAR2] {line.strip()}")

                    p2_process.wait()

                    if p2_process.returncode == 0:
                        log("PAR2 Recovery files created successfully.")
                        # Add par2 files to list
                        # par2 creates .par2, .volXX.par2
                        par2_pattern = par2_base.replace('.par2', '.*.par2')
                        # Wait, simple glob for par2 files matching base
                        # Just grab all par2s created?
                        # Assuming base name match
                        par2_files = glob.glob(os.path.join(parent_dir, archive_name + "*.par2"))
                        generated_files.extend(par2_files)
                    else:
                        log(f"PAR2 creation failed with code {p2_process.returncode}")

            # --- PHASE 3: CLOUD UPLOAD ---
            if upload and remote:
                log("Starting Automatic Cloud Upload...")
                success = RcloneManager.run_upload(generated_files, remote, upload_path)
                if success:
                    NotificationManager.send_notification(f"✅ ParFix: Packed & Uploaded {archive_name} to {remote}")
                else:
                    NotificationManager.send_notification(f"⚠️ ParFix: Packed {archive_name} but Upload Failed")
            else:
                NotificationManager.send_notification(f"✅ ParFix: Packing Complete for {archive_name}")

        except Exception as e:
            log(f"CRITICAL ERROR during archiving: {str(e)}")
            import traceback
            log(traceback.format_exc())
            NotificationManager.send_notification(f"❌ ParFix: Critical Error processing {archive_name}")

class RepairManager:
    @staticmethod
    def run_repair_job(directory, forced_par2=None):
        log(f"Starting repair job in: {directory}")

        try:
            master_par2 = None

            if forced_par2:
                log(f"User selected PAR2 file: {forced_par2}")
                master_par2 = forced_par2
            else:
                # Step 1: Find a suitable PAR2 file
                files = os.listdir(directory)
                # Case-insensitive search
                all_par2 = [f for f in files if f.lower().endswith('.par2')]

                if not all_par2:
                    log("ERROR: No .par2 files found in this directory.")
                    return

                # Priority 1: "Master" files (usually don't have 'vol' in name)
                candidates = [f for f in all_par2 if 'vol' not in f.lower()]
                if candidates:
                    candidates.sort(key=len) # Shortest name is usually the master (Name.par2 vs Name.vol01.par2)
                    master_par2 = candidates[0]
                else:
                    # Priority 2: Any PAR2 file (PAR2 can start from any volume)
                    all_par2.sort()
                    master_par2 = all_par2[0]

            log(f"Using Master PAR2: {master_par2}")

            # Step 2: The Wildcard Repair Strategy
            # par2 r "Master.par2" *
            # This forces par2 to scan ALL files in the dir
            # NOTE: subprocess doesn't expand '*', so we must do it manually
            log("Step 2: Running PAR2 Repair (This may take a while)...")

            # Get all files in directory to simulate shell expansion
            import glob
            all_files = glob.glob(os.path.join(directory, '*'))
            # Filter out the master par2 itself to avoid redundancy, though par2 handles it
            all_files = [os.path.basename(f) for f in all_files]

            cmd = ['par2', 'r', master_par2] + all_files

            process = subprocess.Popen(
                cmd,
                cwd=directory,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True
            )

            # Stream output
            for line in process.stdout:
                line = line.strip()
                if line:
                    # Filter noisy lines if needed, but for now show everything relevant
                    if "Repair is required" in line or "Repair complete" in line or "Ready to recover" in line:
                         log(f"[PAR2] {line}")

            process.wait()

            # Check if repair was successful based on output/exit code
            repair_success = False
            if process.returncode == 0:
                repair_success = True
            else:
                # If exit code non-zero, check logs for explicit success message
                # PAR2 sometimes returns 1/2 but still repaired successfully?
                # Usually exit 0 = OK.
                log(f"PAR2 finished with code {process.returncode}.")

            if not repair_success:
                 # Be strict: if PAR2 didn't exit 0, assume it failed to repair enough blocks.
                 log("CRITICAL: Repair failed. PAR2 exited with error code.")
                 NotificationManager.send_notification(f"❌ ParFix: Repair Failed for {os.path.basename(directory)}")
                 return

            log("PAR2 Repair completed successfully.")

            # Step 3: Attempt Extraction (Attempt 1: As-Is)
            log("Step 3: Extracting RAR archive (Attempt 1)...")
            extract_success = RepairManager.extract_archive(directory)

            if not extract_success:
                log("Extraction failed. Attempting Rename fix (part01 -> part001)...")
                # Step 4: Rename (Fallback)
                RepairManager.cleanup_and_rename(directory, master_par2)

                log("Step 5: Retrying Extraction (Attempt 2)...")
                extract_success = RepairManager.extract_archive(directory)

            if extract_success:
                log("Job Complete!")
                NotificationManager.send_notification(f"✅ ParFix: Repair & Extract Complete for {os.path.basename(directory)}")
            else:
                log("CRITICAL: Extraction failed after repair and rename.")
                NotificationManager.send_notification(f"❌ ParFix: Extraction Failed for {os.path.basename(directory)}")

        except Exception as e:
            log(f"CRITICAL ERROR: {str(e)}")
            import traceback
            log(traceback.format_exc())
            NotificationManager.send_notification(f"❌ ParFix: Repair Failed for {os.path.basename(directory)}")

    @staticmethod
    def cleanup_and_rename(directory, master_par2_name):
        log("Renaming phase: Normalizing part01.rar -> part001.rar...")
        import re
        files = os.listdir(directory)
        for f in files:
            # Check for partX.rar pattern
            match = re.search(r'\.part(\d+)\.rar$', f, re.IGNORECASE)
            if match:
                num_str = match.group(1)
                # Ensure 3 digits for compatibility
                if len(num_str) < 3:
                    new_num = num_str.zfill(3)
                    new_name = f.replace(f".part{num_str}.rar", f".part{new_num}.rar")
                    if new_name != f:
                        log(f"Renaming {f} -> {new_name}")
                        try:
                            os.rename(os.path.join(directory, f), os.path.join(directory, new_name))
                        except OSError as e:
                            log(f"Rename failed: {e}")

    @staticmethod
    def extract_archive(directory):
        # Find the first RAR volume
        files = sorted(os.listdir(directory))
        first_rar = None

        # Priority 1: .rar (if single file or old naming)
        for f in files:
            if f.endswith('.rar') and not '.part' in f:
                first_rar = f
                break

        # Priority 2: .part01.rar or .part001.rar
        if not first_rar:
            for f in files:
                if f.endswith('.part01.rar') or f.endswith('.part001.rar'):
                    first_rar = f
                    break

        if not first_rar:
            log("ERROR: Could not find a suitable RAR file to extract.")
            return False

        log(f"Found archive to extract: {first_rar}")

        cmd = ['unrar', 'x', '-y', first_rar]

        process = subprocess.Popen(
            cmd,
            cwd=directory,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True
        )

        for line in process.stdout:
            if "All OK" in line:
                log("Extraction Successful: All OK")
            elif "Extracting from" in line:
                pass # minor log
            elif "Creating" in line or "Extracting" in line:
                 pass # Too verbose
            else:
                 pass # log(f"[UNRAR] {line.strip()}")

        process.wait()

        if process.returncode == 0:
            log("Unrar finished successfully.")
            return True
        else:
            log(f"Unrar failed with code {process.returncode}")
            return False

class ExtractManager:
    @staticmethod
    def run_extract_job(target_path, method='unrar', password=None):
        # Determine if target is file or dir
        work_dir = target_path
        archive_file = None

        if os.path.isfile(target_path):
            work_dir = os.path.dirname(target_path)
            archive_file = os.path.basename(target_path)
        else:
            # It's a directory, find the archive
            files = sorted(os.listdir(target_path))

            # Smart detection based on method
            if method == 'unrar':
                for f in files:
                    if f.endswith('.rar') and not '.part' in f:
                        archive_file = f
                        break
                if not archive_file:
                    for f in files:
                        if (f.endswith('.part01.rar') or f.endswith('.part001.rar')):
                            archive_file = f
                            break
            elif method == '7z':
                for f in files:
                    if f.endswith('.7z') or f.endswith('.001'):
                        archive_file = f
                        break

        if not archive_file:
            log(f"Extraction Error: No suitable archive found in {work_dir} for method {method}")
            return

        log(f"Starting Extraction: {archive_file} using {method}")

        cmd = []
        if method == 'unrar':
            # unrar x -y -pPASSWORD archive.rar
            cmd = ['unrar', 'x', '-y']
            if password:
                cmd.append(f'-p{password}')
            cmd.append(archive_file)

        elif method == '7z':
            # 7z x -y -pPASSWORD archive.7z
            cmd = ['7z', 'x', '-y']
            if password:
                cmd.append(f'-p{password}')
            cmd.append(archive_file)

        try:
            process = subprocess.Popen(
                cmd,
                cwd=work_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True
            )

            for line in process.stdout:
                line = line.strip()
                if not line: continue

                # Filter noise
                if "Extracting from" in line or "Creating" in line or "Inflating" in line:
                    continue

                if "All OK" in line or "Everything is Ok" in line:
                     log(f"[{method.upper()}] {line}")
                elif "Error" in line or "Wrong password" in line:
                     log(f"[{method.upper()} ERROR] {line}")
                else:
                    # Show periodic progress or important info
                    pass

            process.wait()

            if process.returncode == 0:
                log(f"Extraction with {method} completed successfully.")
                NotificationManager.send_notification(f"✅ ParFix: Extracted {archive_file}")
            else:
                log(f"Extraction failed with code {process.returncode}")
                NotificationManager.send_notification(f"❌ ParFix: Extraction Failed for {archive_file}")

        except Exception as e:
            log(f"Extraction Exception: {e}")

if __name__ == '__main__':
    # Ensure download root exists (useful for local testing)
    if not os.path.exists(DOWNLOAD_ROOT):
        try:
            os.makedirs(DOWNLOAD_ROOT)
        except OSError:
            pass # Might be permission issue in Docker if mapped to host

    # Disable debug for production safety
    app.run(host='0.0.0.0', port=5000, debug=False)
