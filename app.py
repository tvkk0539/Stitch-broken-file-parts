import os
import time
import subprocess
import threading
import queue
import json
import requests
import shutil
import uuid
from flask import Flask, render_template, jsonify, request, Response

app = Flask(__name__)

# Configuration
# Default download directory. In Docker, this should be mapped to the host's download folder.
DOWNLOAD_ROOT = os.environ.get('DOWNLOAD_ROOT', '/data/downloads')
# Support external config mapping or default location
CONFIG_FILE = os.environ.get('CONFIG_FILE', '/app/config.json')

# Global queue for log streaming
log_queue = queue.Queue()

def log(message):
    """Adds a message to the log queue."""
    timestamp = time.strftime("%H:%M:%S")
    formatted_message = f"[{timestamp}] {message}"
    print(formatted_message)  # Also print to stdout for container logs
    log_queue.put(formatted_message)

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

# --- Job Manager System ---

class JobManager:
    def __init__(self):
        self.lock = threading.Lock()
        self.pending_jobs = [] # List of dicts
        self.current_job = None # Dict
        self.current_process = None # subprocess.Popen object
        self._cancelled = False

    def add_job(self, name, target, args=()):
        job_id = str(uuid.uuid4())
        job = {
            'id': job_id,
            'name': name,
            'target': target,
            'args': args,
            'status': 'queued',
            'added_at': time.time()
        }
        with self.lock:
            self.pending_jobs.append(job)
        log(f"Job Queued: {name}")
        return job_id

    def get_next_job(self):
        with self.lock:
            if self.pending_jobs:
                return self.pending_jobs.pop(0)
            return None

    def set_current_job(self, job):
        with self.lock:
            self.current_job = job
            self._cancelled = False
            if job:
                self.current_job['status'] = 'running'
                self.current_job['started_at'] = time.time()

    def set_current_process(self, process):
        """Registers the active subprocess so it can be killed if cancelled."""
        with self.lock:
            self.current_process = process

    def clear_current_process(self):
        with self.lock:
            self.current_process = None

    def is_cancelled(self):
        with self.lock:
            return self._cancelled

    def cancel_job(self, job_id):
        with self.lock:
            # Check if it's the running job
            if self.current_job and self.current_job['id'] == job_id:
                log(f"Cancelling RUNNING job: {self.current_job['name']}")
                self._cancelled = True
                if self.current_process:
                    try:
                        self.current_process.terminate()
                        # Give it a moment, then kill if needed?
                        # Usually terminate is enough for these tools.
                    except Exception as e:
                        log(f"Error terminating process: {e}")
                return True

            # Check pending jobs
            for i, job in enumerate(self.pending_jobs):
                if job['id'] == job_id:
                    removed = self.pending_jobs.pop(i)
                    log(f"Cancelled PENDING job: {removed['name']}")
                    return True

            return False

    def get_status(self):
        with self.lock:
            # Return sanitised copies to avoid race conditions and JSON errors
            def sanitize(job):
                if not job: return None
                j = job.copy()
                if 'target' in j: del j['target']
                # args might contain non-serializable objects too, but usually just strings/ints here.
                # safely convert args to string rep if needed or just leave if we know they are safe.
                # For safety, let's just keep metadata.
                if 'args' in j: del j['args']
                return j

            return {
                'current': sanitize(self.current_job),
                'pending': [sanitize(j) for j in self.pending_jobs]
            }

job_manager = JobManager()

def worker():
    """Background worker that processes jobs from the JobManager."""
    while True:
        job = job_manager.get_next_job()

        if not job:
            time.sleep(1) # Poll for new jobs
            continue

        job_manager.set_current_job(job)
        job_name = job.get('name', 'Unknown Job')
        log(f"Starting Job: {job_name}")

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
            job_manager.set_current_job(None)
            job_manager.clear_current_process()

# Start the worker thread
threading.Thread(target=worker, daemon=True).start()

# --- Task Managers ---

class RcloneManager:
    @staticmethod
    def list_remotes():
        try:
            result = subprocess.run(['rclone', 'listremotes'], capture_output=True, text=True)
            if result.returncode != 0:
                return []
            remotes = [r.strip().rstrip(':') for r in result.stdout.split('\n') if r.strip()]
            return remotes
        except FileNotFoundError:
            return []

    @staticmethod
    def run_upload(source_paths, remote, base_upload_path, transfers=4):
        log(f"Starting Rclone Upload to {remote}:{base_upload_path} (Parallel: {transfers})")

        if not source_paths:
            return True

        # Normalize base upload path (ensure trailing slash)
        if base_upload_path and not base_upload_path.endswith('/'):
            base_upload_path += '/'

        # Process each selected item
        for src_path in source_paths:
            if job_manager.is_cancelled():
                log("Upload job cancelled.")
                break

            try:
                if not os.path.exists(src_path):
                    log(f"Skipping missing file: {src_path}")
                    continue

                basename = os.path.basename(src_path)

                # Determine command based on type
                if os.path.isdir(src_path):
                    # Folder Upload
                    # Destination: base_upload_path + FolderName
                    # rclone copy /local/Folder remote:ParFix_Uploads/Folder
                    dest_path = f"{base_upload_path}{basename}"
                    log(f"Uploading FOLDER: {basename} -> {dest_path}")

                    cmd = ['rclone', 'copy', src_path, f"{remote}:{dest_path}",
                           '--transfers', str(transfers), '--stats', '2s', '-v']
                else:
                    # File Upload
                    # Destination: base_upload_path (rclone copy file remote:path puts it IN path)
                    log(f"Uploading FILE: {basename} -> {base_upload_path}")

                    cmd = ['rclone', 'copy', src_path, f"{remote}:{base_upload_path}",
                           '--transfers', str(transfers), '--stats', '2s', '-v']

                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    universal_newlines=True
                )

                # Register process for cancellation
                job_manager.set_current_process(process)

                for line in process.stdout:
                    line = line.strip()
                    if not line: continue
                    if "error" in line.lower() or "failed" in line.lower():
                        log(f"[RCLONE ERROR] {line}")
                    elif "Transferred:" in line or "Errors:" in line or "Checks:" in line:
                         if "Transferred:" in line: log(f"[UPLOAD] {line}")
                    elif "100%" in line:
                         log(f"[UPLOAD] {line}")

                process.wait()
                if process.returncode != 0:
                    if job_manager.is_cancelled():
                        log(f"Upload cancelled for {basename}")
                        break
                    log(f"Upload failed for {basename} (Code {process.returncode})")
                else:
                    log(f"Upload completed for {basename}")

            except Exception as e:
                log(f"Rclone Error processing {src_path}: {e}")

        return True

class ArchiveManager:
    @staticmethod
    def run_archive_job(source_path, archive_name, split_size, password, fmt='rar', create_par2=True, upload=False, remote=None, upload_path=''):
        parent_dir = os.path.dirname(source_path)
        base_name = os.path.basename(source_path)

        # Extension handling
        ext = '.rar' if fmt == 'rar' else '.7z'
        if not archive_name.endswith(ext):
            archive_name += ext

        log(f"Packing '{base_name}' into '{archive_name}' ({fmt})")

        cmd = []
        if fmt == 'rar':
            cmd = ['rar', 'a', '-m0', f'-v{split_size}', '-ep1']
            if password:
                cmd.append(f'-hp{password}')
            cmd.append(archive_name)
            cmd.append(source_path)
        else:
            size_arg = split_size.lower().replace('m', 'm').replace('g', 'g')
            cmd = ['7z', 'a', f'-v{size_arg}', '-mx0']
            if password:
                cmd.append(f'-p{password}')
                cmd.append('-mhe=on')
            cmd.append(archive_name)
            cmd.append(source_path)

        try:
            if job_manager.is_cancelled(): return

            # --- PHASE 1: ARCHIVING ---
            process = subprocess.Popen(
                cmd,
                cwd=parent_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True
            )
            job_manager.set_current_process(process)

            for line in process.stdout:
                line = line.strip()
                if line and ("%" in line or "Creating" in line or "Done" in line):
                     log(f"[{fmt.upper()}] {line}")

            process.wait()

            if process.returncode != 0:
                if job_manager.is_cancelled():
                    log("Archiving Cancelled")
                else:
                    log(f"Archiving failed (Code {process.returncode})")
                    NotificationManager.send_notification(f"❌ ParFix: Archiving Failed for {archive_name}")
                return

            log("Archive created successfully.")
            generated_files = []

            if job_manager.is_cancelled(): return

            # --- PHASE 2: PAR2 GENERATION ---
            if create_par2:
                log("Starting PAR2 Generation...")
                par2_base = archive_name + ".par2"

                # Determine what files to protect
                import glob
                target_pattern = archive_name.replace('.rar', '.part*.rar') if fmt == 'rar' else archive_name + ".*"

                files_to_protect = glob.glob(os.path.join(parent_dir, target_pattern))
                if fmt == '7z' and not files_to_protect and os.path.exists(os.path.join(parent_dir, archive_name)):
                     files_to_protect = [os.path.join(parent_dir, archive_name)]

                if files_to_protect:
                    files_to_protect.sort()
                    generated_files.extend(files_to_protect)

                    par2_cmd = ['par2', 'c', '-r10', par2_base] + [os.path.basename(f) for f in files_to_protect]

                    p2_process = subprocess.Popen(
                        par2_cmd,
                        cwd=parent_dir,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        universal_newlines=True
                    )
                    job_manager.set_current_process(p2_process)

                    for line in p2_process.stdout:
                        if "Compute" in line or "Constructing" in line:
                             log(f"[PAR2] {line.strip()}")

                    p2_process.wait()
                    if p2_process.returncode == 0:
                        log("PAR2 created.")
                        generated_files.extend(glob.glob(os.path.join(parent_dir, archive_name + "*.par2")))
                    else:
                        if job_manager.is_cancelled():
                            log("PAR2 Cancelled")
                            return
                        log(f"PAR2 failed (Code {p2_process.returncode})")

            if job_manager.is_cancelled(): return

            # --- PHASE 3: CLOUD UPLOAD ---
            if upload and remote:
                RcloneManager.run_upload(generated_files, remote, upload_path)
                NotificationManager.send_notification(f"✅ ParFix: Packed & Uploaded {archive_name}")
            else:
                NotificationManager.send_notification(f"✅ ParFix: Packing Complete for {archive_name}")

        except Exception as e:
            log(f"Error during archiving: {str(e)}")

class RepairManager:
    @staticmethod
    def run_repair_job(directory, forced_par2=None):
        log(f"Starting repair in: {directory}")

        try:
            if job_manager.is_cancelled(): return

            master_par2 = None
            if forced_par2:
                master_par2 = forced_par2
            else:
                files = os.listdir(directory)
                all_par2 = [f for f in files if f.lower().endswith('.par2')]
                if not all_par2:
                    log("ERROR: No .par2 files found.")
                    return

                candidates = [f for f in all_par2 if 'vol' not in f.lower()]
                if candidates:
                    candidates.sort(key=len)
                    master_par2 = candidates[0]
                else:
                    all_par2.sort()
                    master_par2 = all_par2[0]

            log(f"Using Master PAR2: {master_par2}")

            # Step 2: Wildcard Repair
            import glob
            all_files = glob.glob(os.path.join(directory, '*'))
            all_files = [os.path.basename(f) for f in all_files]

            cmd = ['par2', 'r', master_par2] + all_files

            process = subprocess.Popen(
                cmd,
                cwd=directory,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True
            )
            job_manager.set_current_process(process)

            for line in process.stdout:
                line = line.strip()
                if line and ("Repair" in line or "Recover" in line):
                     log(f"[PAR2] {line}")

            process.wait()

            if process.returncode != 0:
                 if job_manager.is_cancelled():
                     log("Repair Cancelled")
                 else:
                     log(f"PAR2 failed (Code {process.returncode})")
                     NotificationManager.send_notification(f"❌ ParFix: Repair Failed")
                 return

            log("PAR2 Repair success.")

            if job_manager.is_cancelled(): return

            # Step 3: Extract
            if RepairManager.extract_archive(directory):
                NotificationManager.send_notification(f"✅ ParFix: Repair & Extract Complete")
            else:
                if job_manager.is_cancelled(): return
                # Rename and retry
                RepairManager.cleanup_and_rename(directory, master_par2)
                if RepairManager.extract_archive(directory):
                    NotificationManager.send_notification(f"✅ ParFix: Repair & Extract Complete (Retry)")
                else:
                    NotificationManager.send_notification(f"❌ ParFix: Extraction Failed")

        except Exception as e:
            log(f"Error: {str(e)}")

    @staticmethod
    def cleanup_and_rename(directory, master_par2_name):
        log("Renaming phase...")
        import re
        files = os.listdir(directory)
        for f in files:
            match = re.search(r'\.part(\d+)\.rar$', f, re.IGNORECASE)
            if match:
                num_str = match.group(1)
                if len(num_str) < 3:
                    new_num = num_str.zfill(3)
                    new_name = f.replace(f".part{num_str}.rar", f".part{new_num}.rar")
                    if new_name != f:
                        try:
                            os.rename(os.path.join(directory, f), os.path.join(directory, new_name))
                        except OSError: pass

    @staticmethod
    def extract_archive(directory):
        files = sorted(os.listdir(directory))
        first_rar = None
        for f in files:
            if f.endswith('.rar') and not '.part' in f:
                first_rar = f
                break
        if not first_rar:
            for f in files:
                if f.endswith('.part01.rar') or f.endswith('.part001.rar'):
                    first_rar = f
                    break

        if not first_rar:
            return False

        log(f"Extracting: {first_rar}")
        cmd = ['unrar', 'x', '-y', first_rar]

        process = subprocess.Popen(
            cmd,
            cwd=directory,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True
        )
        job_manager.set_current_process(process)

        for line in process.stdout:
            if "All OK" in line: log("Unrar OK")

        process.wait()
        return process.returncode == 0

class ExtractManager:
    @staticmethod
    def run_extract_job(target_path, method='unrar', password=None):
        work_dir = target_path
        archive_file = None

        if os.path.isfile(target_path):
            work_dir = os.path.dirname(target_path)
            archive_file = os.path.basename(target_path)
        else:
            files = sorted(os.listdir(target_path))
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
            log(f"No archive found for {method}")
            return

        log(f"Extracting {archive_file} ({method})")

        cmd = []
        if method == 'unrar':
            cmd = ['unrar', 'x', '-y']
            if password: cmd.append(f'-p{password}')
            cmd.append(archive_file)
        elif method == '7z':
            cmd = ['7z', 'x', '-y']
            if password: cmd.append(f'-p{password}')
            cmd.append(archive_file)

        try:
            if job_manager.is_cancelled(): return

            process = subprocess.Popen(
                cmd,
                cwd=work_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True
            )
            job_manager.set_current_process(process)

            for line in process.stdout:
                line = line.strip()
                if "All OK" in line or "Everything is Ok" in line:
                     log(f"[{method.upper()}] {line}")

            process.wait()

            if process.returncode == 0:
                NotificationManager.send_notification(f"✅ ParFix: Extracted {archive_file}")
            else:
                if job_manager.is_cancelled():
                    log("Extraction Cancelled")
                else:
                    log(f"Extraction failed (Code {process.returncode})")

        except Exception as e:
            log(f"Extraction Error: {e}")

# --- API Routes ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/list')
def list_files():
    req_path = request.args.get('path', '')
    abs_path = os.path.join(DOWNLOAD_ROOT, req_path).rstrip('/')

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

    items.sort(key=lambda x: (not x['is_dir'], x['name'].lower()))

    return jsonify({
        'current_path': req_path,
        'parent_path': os.path.dirname(req_path) if req_path else None,
        'items': items
    })

@app.route('/api/logs')
def stream_logs():
    def generate():
        while True:
            try:
                message = log_queue.get(timeout=20)
                yield f"data: {message}\n\n"
            except queue.Empty:
                yield ": keep-alive\n\n"
    return Response(generate(), mimetype='text/event-stream')

# --- Job API ---

@app.route('/api/jobs', methods=['GET'])
def get_jobs():
    return jsonify(job_manager.get_status())

@app.route('/api/jobs/cancel/<job_id>', methods=['POST'])
def cancel_job(job_id):
    success = job_manager.cancel_job(job_id)
    if success:
        return jsonify({'status': 'cancelled'})
    else:
        return jsonify({'error': 'Job not found'}), 404

# --- Action Triggers (Using JobManager) ---

@app.route('/api/repair', methods=['POST'])
def trigger_repair():
    data = request.json
    target_path = data.get('path')
    if not target_path: return jsonify({'error': 'No path'}), 400

    abs_path = os.path.join(DOWNLOAD_ROOT, target_path)
    if not os.path.exists(abs_path): return jsonify({'error': 'Not found'}), 404

    work_dir = abs_path
    target_par2 = None
    if not os.path.isdir(abs_path):
        work_dir = os.path.dirname(abs_path)
        if abs_path.lower().endswith('.par2'):
            target_par2 = os.path.basename(abs_path)

    job_id = job_manager.add_job(
        f"Repair {os.path.basename(target_path)}",
        RepairManager.run_repair_job,
        args=(work_dir, target_par2)
    )
    return jsonify({'status': 'queued', 'job_id': job_id})

@app.route('/api/archive', methods=['POST'])
def trigger_archive():
    data = request.json
    target_path = data.get('path')
    name = data.get('name')
    if not target_path or not name: return jsonify({'error': 'Missing args'}), 400

    abs_path = os.path.join(DOWNLOAD_ROOT, target_path)

    job_id = job_manager.add_job(
        f"Pack {name}",
        ArchiveManager.run_archive_job,
        args=(abs_path, name, data.get('split_size', '1024M'), data.get('password'),
              data.get('format', 'rar'), data.get('create_par2', True),
              data.get('upload', False), data.get('remote'), data.get('upload_path', ''))
    )
    return jsonify({'status': 'queued', 'job_id': job_id})

@app.route('/api/upload', methods=['POST'])
def trigger_manual_upload():
    data = request.json
    target_paths = data.get('paths')
    remote = data.get('remote')
    upload_path = data.get('upload_path', '') # Base path

    if not target_paths or not remote: return jsonify({'error': 'Missing args'}), 400

    abs_paths = [os.path.join(DOWNLOAD_ROOT, p) for p in target_paths]
    abs_paths = [p for p in abs_paths if os.path.exists(p)]

    if not abs_paths: return jsonify({'error': 'No valid paths'}), 400

    transfers = int(data.get('transfers', 4))

    job_id = job_manager.add_job(
        f"Upload {len(abs_paths)} items to {remote}",
        RcloneManager.run_upload,
        args=(abs_paths, remote, upload_path, transfers)
    )
    return jsonify({'status': 'queued', 'job_id': job_id})

@app.route('/api/extract', methods=['POST'])
def trigger_extract():
    data = request.json
    target_path = data.get('path')
    if not target_path: return jsonify({'error': 'Missing path'}), 400

    abs_path = os.path.join(DOWNLOAD_ROOT, target_path)
    if not os.path.exists(abs_path): return jsonify({'error': 'Not found'}), 404

    job_id = job_manager.add_job(
        f"Extract {os.path.basename(target_path)}",
        ExtractManager.run_extract_job,
        args=(abs_path, data.get('method', 'unrar'), data.get('password'))
    )
    return jsonify({'status': 'queued', 'job_id': job_id})

# --- Simple File Ops (Direct, No Queue) ---
# Rename, Delete, Mkdir, Move, Copy are fast enough to keep synchronous usually,
# or we can queue them if they are heavy. Move/Copy might be heavy.
# User asked for job queue control. Move/Copy SHOULD be queued if they are large.
# Current code keeps them sync.
# IMPORTANT: User didn't explicitly ask to queue Move/Copy, but asked for "Queue Tab".
# I'll keep them sync for now to avoid breaking simple flows, but Move/Copy on large files block.
# Let's keep them as is for now unless requested.

@app.route('/api/rename', methods=['POST'])
def rename_item():
    data = request.json
    target_path = data.get('path')
    new_name = data.get('new_name')
    if not target_path or not new_name: return jsonify({'error': 'Args required'}), 400

    abs_path = os.path.join(DOWNLOAD_ROOT, target_path)
    parent = os.path.dirname(abs_path)
    new_abs = os.path.join(parent, new_name)

    if not os.path.abspath(abs_path).startswith(os.path.abspath(DOWNLOAD_ROOT)): return jsonify({'error': 'Denied'}), 403

    try:
        os.rename(abs_path, new_abs)
        log(f"Renamed {target_path} -> {new_name}")
        return jsonify({'status': 'renamed'})
    except Exception as e: return jsonify({'error': str(e)}), 500

@app.route('/api/delete', methods=['POST'])
def trigger_delete():
    data = request.json
    target_paths = data.get('paths', [])
    count = 0
    for p in target_paths:
        abs_path = os.path.join(DOWNLOAD_ROOT, p)
        if os.path.exists(abs_path) and os.path.abspath(abs_path).startswith(os.path.abspath(DOWNLOAD_ROOT)):
            try:
                if os.path.isdir(abs_path): shutil.rmtree(abs_path)
                else: os.remove(abs_path)
                count += 1
                log(f"Deleted {p}")
            except Exception as e: log(f"Error deleting {p}: {e}")
    return jsonify({'status': 'completed', 'deleted': count})

@app.route('/api/mkdir', methods=['POST'])
def make_directory():
    data = request.json
    path = data.get('path', '')
    name = data.get('name')
    if not name: return jsonify({'error': 'Name required'}), 400

    new_dir = os.path.join(DOWNLOAD_ROOT, path, name)
    if not os.path.abspath(new_dir).startswith(os.path.abspath(DOWNLOAD_ROOT)): return jsonify({'error': 'Denied'}), 403

    try:
        os.makedirs(new_dir, exist_ok=True)
        log(f"Created dir {name}")
        return jsonify({'status': 'created'})
    except Exception as e: return jsonify({'error': str(e)}), 500

@app.route('/api/move', methods=['POST'])
def move_items():
    data = request.json
    paths = data.get('paths', [])
    dest = data.get('destination', '')
    abs_dest = os.path.join(DOWNLOAD_ROOT, dest)

    if not os.path.exists(abs_dest): return jsonify({'error': 'Dest not found'}), 404

    count = 0
    for p in paths:
        abs_src = os.path.join(DOWNLOAD_ROOT, p)
        if os.path.exists(abs_src):
            try:
                shutil.move(abs_src, abs_dest)
                count += 1
                log(f"Moved {p}")
            except Exception as e: log(f"Move error {p}: {e}")

    return jsonify({'status': 'completed', 'moved': count})

@app.route('/api/copy', methods=['POST'])
def copy_items():
    data = request.json
    paths = data.get('paths', [])
    dest = data.get('destination', '')
    abs_dest = os.path.join(DOWNLOAD_ROOT, dest)

    if not os.path.exists(abs_dest): return jsonify({'error': 'Dest not found'}), 404

    count = 0
    for p in paths:
        abs_src = os.path.join(DOWNLOAD_ROOT, p)
        if os.path.exists(abs_src):
            try:
                basename = os.path.basename(abs_src)
                final = os.path.join(abs_dest, basename)
                if os.path.isdir(abs_src): shutil.copytree(abs_src, final, dirs_exist_ok=True)
                else: shutil.copy2(abs_src, final)
                count += 1
                log(f"Copied {p}")
            except Exception as e: log(f"Copy error {p}: {e}")

    return jsonify({'status': 'completed', 'copied': count})

@app.route('/api/settings', methods=['GET', 'POST'])
def settings():
    if request.method == 'POST':
        save_config(request.json)
        return jsonify({'status': 'saved'})
    return jsonify(load_config())

@app.route('/api/remotes')
def get_remotes():
    return jsonify(RcloneManager.list_remotes())

if __name__ == '__main__':
    if not os.path.exists(DOWNLOAD_ROOT):
        try: os.makedirs(DOWNLOAD_ROOT)
        except: pass
    app.run(host='0.0.0.0', port=5000, debug=False)
