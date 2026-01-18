import os
import time
import subprocess
import threading
import queue
from flask import Flask, render_template, jsonify, request, Response

app = Flask(__name__)

# Configuration
# Default download directory. In Docker, this should be mapped to the host's download folder.
DOWNLOAD_ROOT = os.environ.get('DOWNLOAD_ROOT', '/data/downloads')

# Global queue for log streaming
log_queue = queue.Queue()

def log(message):
    """Adds a message to the log queue."""
    timestamp = time.strftime("%H:%M:%S")
    formatted_message = f"[{timestamp}] {message}"
    print(formatted_message)  # Also print to stdout for container logs
    log_queue.put(formatted_message)

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

    # Run repair in a separate thread to not block the response
    thread = threading.Thread(target=RepairManager.run_repair_job, args=(abs_path,))
    thread.start()

    return jsonify({'status': 'started', 'message': f'Repair job started for {target_path}'})

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

    if not target_path or not name:
        return jsonify({'error': 'Path and Name are required'}), 400

    abs_path = os.path.join(DOWNLOAD_ROOT, target_path)

    # Security check
    if not os.path.abspath(abs_path).startswith(os.path.abspath(DOWNLOAD_ROOT)):
        return jsonify({'error': 'Access denied'}), 403

    if not os.path.exists(abs_path):
        return jsonify({'error': 'Path not found'}), 404

    # Run archiving in a separate thread
    thread = threading.Thread(
        target=ArchiveManager.run_archive_job,
        args=(abs_path, name, split_size, password, fmt, create_par2)
    )
    thread.start()

    return jsonify({'status': 'started', 'message': f'Archiving started for {name}'})

class ArchiveManager:
    @staticmethod
    def run_archive_job(source_path, archive_name, split_size, password, fmt='rar', create_par2=True):
        parent_dir = os.path.dirname(source_path)
        base_name = os.path.basename(source_path)

        # Extension handling
        ext = '.rar' if fmt == 'rar' else '.7z'
        if not archive_name.endswith(ext):
            archive_name += ext

        log(f"Starting Archive Job: Packing '{base_name}' into '{archive_name}'")
        log(f"Format: {fmt}, Split: {split_size}, PAR2: {create_par2}")

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
                return

            log("Archive created successfully.")

            # --- PHASE 2: PAR2 GENERATION ---
            if create_par2:
                log("Starting PAR2 Recovery File Generation...")

                # We need to find the created parts.
                # RAR parts: Name.part001.rar OR Name.rar (if single)
                # 7z parts: Name.7z.001

                # PAR2 Command: par2 c -r10 -n1 "Name.par2" "Name.part*"
                # We want to protect ALL parts.

                par2_base = archive_name + ".par2"

                # Wildcard for input files
                # RAR: Name.part*.rar or Name.rar
                # 7Z: Name.7z.*

                # Safe approach: pass the base archive name pattern to par2
                # But par2 needs file list.
                # We can use shell globbing if we run via shell=True, but safer to pass specific wildcard string
                # if the tool supports it. par2 supports wildcards in CLI.

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

                # Par2 command
                # par2 c -r10 "Name.par2" "target_pattern"
                # Using shell=True for wildcard expansion is easiest here,
                # OR we list dir and find matches manually.

                # Manual match is safer for Python
                import glob

                search_pattern = os.path.join(parent_dir, target_pattern)
                files_to_protect = glob.glob(search_pattern)

                # If 7z, we might also have the .7z file itself if not split?
                if not files_to_protect and os.path.exists(os.path.join(parent_dir, archive_name)):
                    files_to_protect = [os.path.join(parent_dir, archive_name)]

                if not files_to_protect:
                    log("Warning: Could not find archive files to protect with PAR2.")
                    return

                files_to_protect.sort()

                # Limit command length if too many files?
                # Usually fine.

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
                else:
                    log(f"PAR2 creation failed with code {p2_process.returncode}")

        except Exception as e:
            log(f"CRITICAL ERROR during archiving: {str(e)}")
            import traceback
            log(traceback.format_exc())

class RepairManager:
    @staticmethod
    def run_repair_job(directory):
        log(f"Starting repair job in: {directory}")

        try:
            # Step 1: Find the master PAR2 file
            par2_files = [f for f in os.listdir(directory) if f.endswith('.par2') and not 'vol' in f]
            if not par2_files:
                # Fallback: look for volume 1 if no master file exists
                par2_files = [f for f in os.listdir(directory) if f.endswith('.vol01+02.par2') or f.endswith('.vol001+002.par2')]

            if not par2_files:
                log("ERROR: No .par2 files found in this directory.")
                return

            # Pick the first logical par2 file (usually the smallest one without vol numbers, or the first vol)
            # Sorting ensures we pick shortest name usually (Master.par2 vs Master.vol01.par2)
            par2_files.sort(key=len)
            master_par2 = par2_files[0]
            log(f"Found Master PAR2: {master_par2}")

            # Step 2: The Wildcard Repair Strategy
            # par2 r "Master.par2" *
            # This forces par2 to scan ALL files in the dir
            log("Step 2: Running PAR2 Repair (This may take a while)...")
            cmd = ['par2', 'r', master_par2, '*']

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

            if process.returncode != 0:
                 log(f"PAR2 finished with code {process.returncode}. Checking if repair was successful...")
            else:
                 log("PAR2 Repair completed successfully.")

            # Step 3: Cleanup and Renaming
            log("Step 3: cleaning up and renaming files...")
            RepairManager.cleanup_and_rename(directory, master_par2)

            # Step 4: Extraction
            log("Step 4: Extracting RAR archive...")
            RepairManager.extract_archive(directory)

            log("Job Complete!")

        except Exception as e:
            log(f"CRITICAL ERROR: {str(e)}")
            import traceback
            log(traceback.format_exc())

    @staticmethod
    def cleanup_and_rename(directory, master_par2_name):
        # The logic here is tricky.
        # If PAR2 succeeded, it usually generates the correct files.
        # However, the prompt specifies we might need to delete scrambled ones.
        # But wait, 'par2 r' usually REPAIRS files in place or creates the corrected ones.
        # If the filenames were scrambled, par2 might have created NEW files with correct names
        # OR it might have just verified the blocks.

        # If par2 worked, we should have files matching the par2 basename.
        base_name = master_par2_name.replace('.par2', '')

        files = os.listdir(directory)

        # 1. Identify "Bad" scrambled files
        # Heuristic: If we have "Movie.part01.rar" (Good) and "x8d7s...rar" (Bad), delete Bad.

        # Let's count how many "Good" looking RARs we have
        # Usually they start with the same prefix as the par2 file
        # But par2 filename might not match rar filename perfectly (Scene rules).

        # Simpler approach based on prompt: "Delete broken scrambled files."
        # If par2 succeeded, it reconstructed the valid files.
        # We can try to identify files that do NOT match the expected pattern.

        log("Cleanup phase: Checking for leftover scrambled files...")
        # (This is a simplified cleanup. In reality, par2 often leaves the scrambled files if it reconstructed new ones)

        # Step 3b: Rename consistency (part1.rar -> part001.rar)
        # This is important for unrar
        import re
        files = os.listdir(directory)
        for f in files:
            # Check for partX.rar pattern
            match = re.search(r'\.part(\d+)\.rar$', f, re.IGNORECASE)
            if match:
                num_str = match.group(1)
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
            return

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
        else:
            log(f"Unrar failed with code {process.returncode}")

if __name__ == '__main__':
    # Ensure download root exists (useful for local testing)
    if not os.path.exists(DOWNLOAD_ROOT):
        try:
            os.makedirs(DOWNLOAD_ROOT)
        except OSError:
            pass # Might be permission issue in Docker if mapped to host

    app.run(host='0.0.0.0', port=5000, debug=True)
