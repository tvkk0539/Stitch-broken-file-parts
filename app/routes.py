from flask import Blueprint, render_template, jsonify, request, Response
from app.core.job_manager import log_queue, job_manager, log
from app.managers.rclone import RcloneManager
from app.managers.archive import ArchiveManager
from app.managers.repair import RepairManager
from app.managers.extract import ExtractManager
from app.managers.inspector import InspectorManager
from app.managers.github_tool import GitHubManager
from app.core.config import save_config, load_config
import os
import shutil
import subprocess
import psutil

bp = Blueprint('main', __name__)

DOWNLOAD_ROOT = os.environ.get('DOWNLOAD_ROOT', '/data/downloads')

@bp.route('/')
def index():
    return render_template('index.html')

@bp.route('/api/list')
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

@bp.route('/api/system/stats')
def system_stats():
    # Disk Usage
    try:
        total, used, free = shutil.disk_usage(DOWNLOAD_ROOT)
        disk_percent = (used / total) * 100
        disk_free_gb = free / (1024**3)
    except:
        disk_percent = 0
        disk_free_gb = 0

    # CPU & RAM
    cpu_percent = psutil.cpu_percent(interval=None)
    mem = psutil.virtual_memory()

    return jsonify({
        'disk': {
            'percent': round(disk_percent, 1),
            'free_gb': round(disk_free_gb, 1)
        },
        'cpu': round(cpu_percent, 1),
        'ram': round(mem.percent, 1)
    })

@bp.route('/api/logs')
def stream_logs():
    def generate():
        while True:
            try:
                message = log_queue.get(timeout=20)
                yield f"data: {message}\n\n"
            except: # queue.Empty
                yield ": keep-alive\n\n"
    return Response(generate(), mimetype='text/event-stream')

# --- Job API ---

@bp.route('/api/jobs', methods=['GET'])
def get_jobs():
    return jsonify(job_manager.get_status())

@bp.route('/api/jobs/history/clear', methods=['POST'])
def clear_history():
    job_manager.clear_history()
    return jsonify({'status': 'cleared'})

@bp.route('/api/jobs/cancel/<job_id>', methods=['POST'])
def cancel_job(job_id):
    success = job_manager.cancel_job(job_id)
    if success:
        return jsonify({'status': 'cancelled'})
    else:
        return jsonify({'error': 'Job not found'}), 404

# --- Action Triggers (Using JobManager) ---

@bp.route('/api/repair', methods=['POST'])
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

@bp.route('/api/archive', methods=['POST'])
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

@bp.route('/api/upload', methods=['POST'])
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

    # Get names for display
    display_names = [os.path.basename(p) for p in abs_paths]

    job_id = job_manager.add_job(
        f"Upload {len(abs_paths)} items to {remote}",
        RcloneManager.run_upload,
        args=(abs_paths, remote, upload_path, transfers),
        initial_details={'targets': display_names}
    )
    return jsonify({'status': 'queued', 'job_id': job_id})

@bp.route('/api/extract', methods=['POST'])
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

@bp.route('/api/inspect', methods=['POST'])
def inspect_item():
    data = request.json

    # Handle batch inspection
    paths = data.get('paths')
    if paths:
        abs_paths = [os.path.join(DOWNLOAD_ROOT, p) for p in paths]
        abs_paths = [p for p in abs_paths if os.path.exists(p)]
        if not abs_paths: return jsonify({'error': 'No valid paths'}), 404

        info = InspectorManager.inspect_batch(abs_paths)
        return jsonify(info)

    # Legacy single path handling
    path = data.get('path')
    if not path: return jsonify({'error': 'No path'}), 400

    abs_path = os.path.join(DOWNLOAD_ROOT, path)
    if not os.path.exists(abs_path): return jsonify({'error': 'Not found'}), 404

    info = InspectorManager.inspect_item(abs_path)
    return jsonify(info)

@bp.route('/api/rename', methods=['POST'])
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

@bp.route('/api/delete', methods=['POST'])
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

@bp.route('/api/mkdir', methods=['POST'])
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

@bp.route('/api/move', methods=['POST'])
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

@bp.route('/api/copy', methods=['POST'])
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

@bp.route('/api/settings', methods=['GET', 'POST'])
def settings():
    if request.method == 'POST':
        save_config(request.json)
        return jsonify({'status': 'saved'})
    return jsonify(load_config())

@bp.route('/api/remotes')
def get_remotes():
    return jsonify(RcloneManager.list_remotes())

@bp.route('/api/rclone/list', methods=['GET'])
def list_rclone_path():
    remote = request.args.get('remote')
    path = request.args.get('path', '')
    if not remote: return jsonify({'error': 'Remote required'}), 400

    return jsonify(RcloneManager.list_path(remote, path))

@bp.route('/api/rclone/download', methods=['POST'])
def trigger_rclone_download():
    data = request.json
    remote = data.get('remote')
    paths = data.get('paths', [])
    transfers = int(data.get('transfers', 4))
    destination = data.get('destination', '') # Relative to DOWNLOAD_ROOT

    if not remote or not paths: return jsonify({'error': 'Missing args'}), 400

    # Construct absolute download path
    dest_abs = os.path.join(DOWNLOAD_ROOT, destination) if destination else DOWNLOAD_ROOT

    display_names = [os.path.basename(p) for p in paths]

    job_id = job_manager.add_job(
        f"Download {len(paths)} items from {remote}",
        RcloneManager.run_download,
        args=(remote, paths, dest_abs, transfers),
        initial_details={'targets': display_names}
    )
    return jsonify({'status': 'queued', 'job_id': job_id})

@bp.route('/api/rclone/move', methods=['POST'])
def trigger_rclone_move():
    data = request.json
    remote = data.get('remote')
    paths = data.get('paths', [])
    dest = data.get('destination', '')
    dest_remote = data.get('dest_remote') # Optional: for cross-remote move

    if not remote or not paths: return jsonify({'error': 'Missing args'}), 400

    job_id = job_manager.add_job(
        f"Move {len(paths)} items in Cloud",
        RcloneManager.run_cloud_move,
        args=(remote, paths, dest, dest_remote)
    )
    return jsonify({'status': 'queued', 'job_id': job_id})

@bp.route('/api/rclone/copy', methods=['POST'])
def trigger_rclone_copy():
    data = request.json
    remote = data.get('remote')
    paths = data.get('paths', [])
    dest = data.get('destination', '')
    dest_remote = data.get('dest_remote') # Optional: for cross-remote copy

    if not remote or not paths: return jsonify({'error': 'Missing args'}), 400

    job_id = job_manager.add_job(
        f"Copy {len(paths)} items in Cloud",
        RcloneManager.run_cloud_copy,
        args=(remote, paths, dest, dest_remote)
    )
    return jsonify({'status': 'queued', 'job_id': job_id})

@bp.route('/api/rclone/delete', methods=['POST'])
def trigger_rclone_delete():
    data = request.json
    remote = data.get('remote')
    paths = data.get('paths', [])

    if not remote or not paths: return jsonify({'error': 'Missing args'}), 400

    job_id = job_manager.add_job(
        f"Delete {len(paths)} items from Cloud",
        RcloneManager.delete_items_job,
        args=(remote, paths)
    )
    return jsonify({'status': 'queued', 'job_id': job_id})

@bp.route('/api/rclone/mkdir', methods=['POST'])
def trigger_rclone_mkdir():
    data = request.json
    remote = data.get('remote')
    path = data.get('path', '')
    name = data.get('name')

    if not remote or not name: return jsonify({'error': 'Missing args'}), 400

    try:
        RcloneManager.mkdir_sync(remote, path, name)
        return jsonify({'status': 'created'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/api/rclone/rename', methods=['POST'])
def trigger_rclone_rename():
    data = request.json
    remote = data.get('remote')
    path = data.get('path') # Relative path
    new_name = data.get('new_name')

    if not remote or not path or not new_name: return jsonify({'error': 'Missing args'}), 400

    try:
        RcloneManager.rename_sync(remote, path, new_name)
        return jsonify({'status': 'renamed'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/api/settings/upload-config', methods=['POST'])
def upload_config():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if file:
        try:
            res = subprocess.run(['rclone', 'config', 'file'], capture_output=True, text=True)
            lines = res.stdout.strip().split('\n')
            conf_path = lines[-1].strip()

            os.makedirs(os.path.dirname(conf_path), exist_ok=True)
            file.save(conf_path)
            log(f"Rclone config uploaded to {conf_path}")
            return jsonify({'status': 'uploaded', 'path': conf_path})
        except Exception as e:
            return jsonify({'error': f"Failed to save config: {e}"}), 500

# --- Apps: GitHub ---

@bp.route('/api/apps/github/accounts', methods=['GET'])
def github_list_accounts():
    return jsonify(GitHubManager.list_accounts())

@bp.route('/api/apps/github/login', methods=['POST'])
def github_login():
    data = request.json
    token = data.get('token')
    if not token: return jsonify({'error': 'Token required'}), 400

    return jsonify(GitHubManager.add_account(token))

@bp.route('/api/apps/github/logout', methods=['POST'])
def github_logout():
    data = request.json
    account_id = data.get('id')
    if not account_id: return jsonify({'error': 'ID required'}), 400

    return jsonify(GitHubManager.remove_account(account_id))

@bp.route('/api/apps/github/user/repos', methods=['GET'])
def github_list_user_repos():
    account_id = request.args.get('account_id')
    if not account_id: return jsonify({'error': 'Account ID required'}), 400

    return jsonify(GitHubManager.list_user_repos(account_id))

@bp.route('/api/apps/github/repo/visibility', methods=['POST'])
def github_set_visibility():
    data = request.json
    repo = data.get('repo')
    private = data.get('private')
    account_id = data.get('account_id')

    if not repo or not account_id: return jsonify({'error': 'Missing args'}), 400

    return jsonify(GitHubManager.update_repo_visibility(repo, private, account_id))

@bp.route('/api/apps/github/releases', methods=['POST'])
def github_get_releases():
    data = request.json
    repo = data.get('repo')
    account_id = data.get('account_id')
    if not repo: return jsonify({'error': 'Repo required'}), 400

    return jsonify(GitHubManager.get_releases(repo, account_id))

@bp.route('/api/apps/github/download', methods=['POST'])
def github_download():
    data = request.json
    url = data.get('url')
    filename = data.get('filename')
    path = data.get('path', '') # Relative path
    account_id = data.get('account_id')

    if not url or not filename: return jsonify({'error': 'Missing args'}), 400

    abs_dest = os.path.join(DOWNLOAD_ROOT, path)

    job_id = job_manager.add_job(
        f"GitHub Download: {filename}",
        GitHubManager.run_download_job,
        args=(url, filename, abs_dest, account_id)
    )
    return jsonify({'status': 'queued', 'job_id': job_id})

@bp.route('/api/apps/github/download/batch', methods=['POST'])
def github_download_batch():
    data = request.json
    assets = data.get('assets') # List of {url, filename}
    path = data.get('path', '')
    account_id = data.get('account_id')

    if not assets: return jsonify({'error': 'Assets required'}), 400

    abs_dest = os.path.join(DOWNLOAD_ROOT, path)

    job_id = job_manager.add_job(
        f"GitHub Batch Download ({len(assets)} items)",
        GitHubManager.run_batch_download_job,
        args=(assets, abs_dest, account_id)
    )
    return jsonify({'status': 'queued', 'job_id': job_id})

@bp.route('/api/apps/github/release/delete', methods=['POST'])
def github_delete_release():
    data = request.json
    owner = data.get('owner')
    repo = data.get('repo')
    release_id = data.get('release_id')
    account_id = data.get('account_id')
    if not release_id: return jsonify({'error': 'ID required'}), 400
    return jsonify(GitHubManager.delete_release(owner, repo, release_id, account_id))

@bp.route('/api/apps/github/release/asset/delete', methods=['POST'])
def github_delete_asset():
    data = request.json
    owner = data.get('owner')
    repo = data.get('repo')
    asset_id = data.get('asset_id')
    account_id = data.get('account_id')
    if not asset_id: return jsonify({'error': 'ID required'}), 400
    return jsonify(GitHubManager.delete_release_asset(owner, repo, asset_id, account_id))

@bp.route('/api/apps/github/publish', methods=['POST'])
def github_publish():
    data = request.json
    repo = data.get('repo')
    tag = data.get('tag')
    file_path = data.get('file_path') # Relative
    account_id = data.get('account_id')

    # Rich Options
    body = data.get('body')
    draft = data.get('draft', False)
    prerelease = data.get('prerelease', False)

    if not repo or not tag or not file_path: return jsonify({'error': 'Missing args'}), 400
    if not account_id: return jsonify({'error': 'Account ID required'}), 400

    abs_file = os.path.join(DOWNLOAD_ROOT, file_path)
    if not os.path.exists(abs_file): return jsonify({'error': 'File not found'}), 404

    job_id = job_manager.add_job(
        f"GitHub Publish: {tag}",
        GitHubManager.run_publish_job,
        args=(repo, tag, abs_file, account_id, body, prerelease, draft)
    )
    return jsonify({'status': 'queued', 'job_id': job_id})

@bp.route('/api/apps/github/repo/create', methods=['POST'])
def github_create_repo():
    data = request.json
    name = data.get('name')
    private = data.get('private', False)
    description = data.get('description', '')
    account_id = data.get('account_id')

    if not name or not account_id: return jsonify({'error': 'Missing args'}), 400

    return jsonify(GitHubManager.create_repository(name, private, description, account_id))

@bp.route('/api/apps/github/repo/rename', methods=['POST'])
def github_rename_repo():
    data = request.json
    owner = data.get('owner')
    repo = data.get('repo')
    new_name = data.get('new_name')
    account_id = data.get('account_id')

    if not owner or not repo or not new_name or not account_id: return jsonify({'error': 'Missing args'}), 400

    return jsonify(GitHubManager.rename_repository(owner, repo, new_name, account_id))

@bp.route('/api/apps/github/repo/delete', methods=['POST'])
def github_delete_repo():
    data = request.json
    owner = data.get('owner')
    repo = data.get('repo')
    account_id = data.get('account_id')

    if not owner or not repo or not account_id: return jsonify({'error': 'Missing args'}), 400

    return jsonify(GitHubManager.delete_repository(owner, repo, account_id))

@bp.route('/api/apps/github/repo/clone', methods=['POST'])
def github_clone_repo():
    data = request.json
    url = data.get('url')
    path = data.get('path', '')
    account_id = data.get('account_id')

    if not url: return jsonify({'error': 'URL required'}), 400

    abs_dest = os.path.join(DOWNLOAD_ROOT, path)

    job_id = job_manager.add_job(
        f"Git Clone: {os.path.basename(url)}",
        GitHubManager.clone_repository_job,
        args=(url, abs_dest, account_id)
    )
    return jsonify({'status': 'queued', 'job_id': job_id})

@bp.route('/api/apps/github/repo/import', methods=['POST'])
def github_import_repo():
    data = request.json
    source_url = data.get('source_url')
    target_name = data.get('target_name')
    private = data.get('private', False)
    account_id = data.get('account_id')

    if not source_url or not target_name or not account_id:
        return jsonify({'error': 'Missing args'}), 400

    job_id = job_manager.add_job(
        f"Import Repo: {target_name}",
        GitHubManager.run_import_job,
        args=(source_url, target_name, private, account_id)
    )
    return jsonify({'status': 'queued', 'job_id': job_id})

# --- Actions ---
@bp.route('/api/apps/github/actions/workflows', methods=['POST'])
def github_list_workflows():
    data = request.json
    return jsonify(GitHubManager.list_workflows(data.get('repo'), data.get('account_id')))

@bp.route('/api/apps/github/actions/runs', methods=['POST'])
def github_list_runs():
    data = request.json
    return jsonify(GitHubManager.list_workflow_runs(data.get('repo'), data.get('account_id')))

@bp.route('/api/apps/github/actions/run', methods=['POST'])
def github_trigger_run():
    data = request.json
    return jsonify(GitHubManager.trigger_workflow(data.get('repo'), data.get('id'), data.get('ref', 'main'), data.get('account_id')))

@bp.route('/api/apps/github/actions/cancel', methods=['POST'])
def github_cancel_run():
    data = request.json
    return jsonify(GitHubManager.cancel_workflow_run(data.get('repo'), data.get('id'), data.get('account_id')))
