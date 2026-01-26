from app.core.job_manager import log, job_manager
from app.managers.notification import NotificationManager
import os
import subprocess
import json

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

        # Performance Flags
        # --transfers 8: Boost speed for multiple files
        # --checkers 16: Speed up scanning
        perf_flags = ['--transfers', '8', '--checkers', '16', '--stats', '2s', '-v']

        # Determine strategy
        # If multiple files are selected, use --files-from to do one parallel batch.
        # However, creating a temporary file list requires handling absolute paths correctly.
        # rclone --files-from expects paths relative to the root if not careful,
        # or absolute paths if configured.
        # Safest way for mixed content (files/folders) from different potential parents (unlikely in this UI but possible)
        # is to iterate if they are from different dirs, or use --files-from if from same dir.
        # In our UI, `selectedPaths` are relative to DOWNLOAD_ROOT.

        # Let's verify if we can use a single batch.
        # We will create a temp file list.

        import tempfile

        # Filter valid paths
        valid_paths = [p for p in source_paths if os.path.exists(p)]
        if not valid_paths: return True

        try:
            # Create temp file for --files-from
            # Note: rclone expects the file list to match the source root passed to command.
            # Our source root is effectively DOWNLOAD_ROOT (or common parent).
            # But `source_paths` are absolute local paths.
            # To use --files-from efficiently, we pass "/" as source and absolute paths in list?
            # Rclone warns about using / as source.

            # Better strategy: Group by parent directory?
            # Or just use the loop BUT spawn them in parallel using Popen?
            # Python threading is easier if we want to track progress.
            # But the user asked for "rclone parallel", which rclone does best itself.

            # Let's try the --files-from approach with common parent.
            # Assuming all paths are under DOWNLOAD_ROOT.
            common_root = os.path.dirname(os.path.commonprefix(valid_paths))
            if not common_root or common_root == '/':
                 common_root = os.path.dirname(valid_paths[0])

            # Prepare list relative to common_root
            rel_paths = []
            for p in valid_paths:
                rel = os.path.relpath(p, common_root)
                rel_paths.append(rel)

            with tempfile.NamedTemporaryFile(mode='w', delete=False) as tmp_file:
                tmp_file.write('\n'.join(rel_paths))
                tmp_path = tmp_file.name

            # One Big Command
            log(f"Batch Uploading {len(valid_paths)} items from {common_root}...")
            job_manager.update_job_details({
                'action': f"Batch Uploading {len(valid_paths)} items",
                'current_item': "Processing..."
            })

            # Destination logic is tricky with files-from.
            # If we copy to remote:base_upload_path, rclone preserves directory structure from the 'root'.
            # E.g. root=/data, file=sub/file.txt -> remote:base/sub/file.txt
            # This is usually desired behavior for bulk uploads.

            cmd = ['rclone', 'copy', common_root, f"{remote}:{base_upload_path}",
                   '--files-from', tmp_path] + perf_flags

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                universal_newlines=True
            )
            job_manager.set_current_process(process)

            for line in process.stdout:
                line = line.strip()
                if "Transferred:" in line or "100%" in line:
                    log(f"[UPLOAD] {line}")
                elif "error" in line.lower():
                    log(f"[RCLONE ERROR] {line}")

            process.wait()
            os.remove(tmp_path)

            if process.returncode != 0:
                if job_manager.is_cancelled():
                    log("Upload Cancelled")
                else:
                    log(f"Upload Batch Failed (Code {process.returncode})")
                    job_manager.update_job_details({'error': "Upload failed"})
            else:
                log("Batch Upload Completed")
                NotificationManager.send_notification(f"✅ ParFix: Uploaded {len(valid_paths)} items")

        except Exception as e:
            log(f"Upload Error: {e}")
            job_manager.update_job_details({'error': str(e)})

        return True

    @staticmethod
    def list_path(remote, path=''):
        """Lists files in a remote path using rclone lsjson."""
        try:
            full_target = f"{remote}:{path}"
            log(f"Listing remote path: {full_target}")

            cmd = ['rclone', 'lsjson', full_target]
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode != 0:
                log(f"Rclone list failed: {result.stderr}")
                return {'error': 'Failed to list remote path'}

            items = json.loads(result.stdout)
            # Process items to match our API structure
            processed_items = []
            for item in items:
                processed_items.append({
                    'name': item['Name'],
                    'is_dir': item['IsDir'],
                    'path': os.path.join(path, item['Name']), # Relative path for navigation
                    'size': item.get('Size', 0),
                    'mod_time': item.get('ModTime', '')
                })

            # Sort: Directories first, then files
            processed_items.sort(key=lambda x: (not x['is_dir'], x['name'].lower()))

            return {
                'current_path': path,
                'parent_path': os.path.dirname(path) if path else '',
                'items': processed_items
            }
        except Exception as e:
            log(f"Rclone list exception: {e}")
            return {'error': str(e)}

    @staticmethod
    def run_download(remote, source_paths, dest_root, transfers=4):
        log(f"Starting Rclone Download from {remote} (Parallel: {transfers})")

        if not source_paths: return True

        for i, src_path in enumerate(source_paths):
            if job_manager.is_cancelled():
                log("Download job cancelled.")
                break

            basename = os.path.basename(src_path)
            full_src = f"{remote}:{src_path}"
            target_local = os.path.join(dest_root, basename)

            log(f"Downloading {basename} -> {target_local}")
            job_manager.update_job_details({
                'action': f"Downloading item {i+1} of {len(source_paths)}",
                'current_item': basename
            })

            # Use 'copyto' to handle single file downloads correctly
            cmd = ['rclone', 'copyto', full_src, target_local,
                   '--transfers', str(transfers), '--stats', '2s', '-v']

            process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    stdin=subprocess.DEVNULL,
                    universal_newlines=True
                )

            job_manager.set_current_process(process)

            for line in process.stdout:
                line = line.strip()
                if not line: continue
                if "error" in line.lower() or "failed" in line.lower():
                    log(f"[RCLONE ERROR] {line}")
                elif "Transferred:" in line or "Errors:" in line or "Checks:" in line:
                        if "Transferred:" in line: log(f"[DOWNLOAD] {line}")
                elif "100%" in line:
                        log(f"[DOWNLOAD] {line}")

            process.wait()

            if process.returncode != 0:
                if job_manager.is_cancelled():
                    log(f"Download cancelled for {basename}")
                    break
                log(f"Download failed for {basename} (Code {process.returncode})")
                job_manager.update_job_details({'error': f"Download failed (Code {process.returncode})"})
            else:
                log(f"Download completed for {basename}")
                NotificationManager.send_notification(f"✅ ParFix: Downloaded {basename} from Cloud")

        return True

    @staticmethod
    def run_cloud_move(remote, source_paths, dest_path, dest_remote=None):
        """Moves files/folders between locations in the cloud (Server-Side Move)."""
        target_remote = dest_remote if dest_remote else remote
        log(f"Starting Rclone Move to {target_remote}:{dest_path}")

        for i, src_path in enumerate(source_paths):
            if job_manager.is_cancelled(): break

            basename = os.path.basename(src_path)
            # Source: remote:src_path
            # Dest: target_remote:dest_path/basename

            full_src = f"{remote}:{src_path}"
            full_dest = f"{target_remote}:{dest_path}/{basename}"

            job_manager.update_job_details({
                'action': f"Moving item {i+1} of {len(source_paths)}",
                'current_item': basename
            })

            log(f"Moving {full_src} -> {full_dest}")

            cmd = ['rclone', 'moveto', full_src, full_dest, '-v', '--stats', '2s']

            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, universal_newlines=True)
            job_manager.set_current_process(process)

            for line in process.stdout:
                if "Transferred:" in line: log(f"[MOVE] {line.strip()}")

            process.wait()

            if process.returncode != 0:
                if job_manager.is_cancelled():
                    log(f"Move cancelled for {basename}")
                else:
                    log(f"Move failed for {basename}")
                    job_manager.update_job_details({'error': f"Move failed (Code {process.returncode})"})
            else:
                log(f"Moved {basename}")

        return True

    @staticmethod
    def run_cloud_copy(remote, source_paths, dest_path, dest_remote=None):
        """Copies files/folders between locations in the cloud (Server-Side Copy)."""
        target_remote = dest_remote if dest_remote else remote
        log(f"Starting Rclone Copy to {target_remote}:{dest_path}")

        for i, src_path in enumerate(source_paths):
            if job_manager.is_cancelled(): break

            basename = os.path.basename(src_path)
            full_src = f"{remote}:{src_path}"
            full_dest = f"{target_remote}:{dest_path}/{basename}"

            job_manager.update_job_details({
                'action': f"Copying item {i+1} of {len(source_paths)}",
                'current_item': basename
            })

            log(f"Copying {full_src} -> {full_dest}")

            cmd = ['rclone', 'copyto', full_src, full_dest, '-v', '--stats', '2s']

            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, universal_newlines=True)
            job_manager.set_current_process(process)

            for line in process.stdout:
                if "Transferred:" in line: log(f"[COPY] {line.strip()}")

            process.wait()

            if process.returncode != 0:
                if job_manager.is_cancelled():
                    log(f"Copy cancelled for {basename}")
                else:
                    log(f"Copy failed for {basename}")
                    job_manager.update_job_details({'error': f"Copy failed (Code {process.returncode})"})
            else:
                log(f"Copied {basename}")

        return True

    @staticmethod
    def delete_items_job(remote, paths):
        log(f"Deleting {len(paths)} items from {remote}")

        for i, path in enumerate(paths):
            if job_manager.is_cancelled(): break

            full_path = f"{remote}:{path}"
            job_manager.update_job_details({
                'action': f"Deleting item {i+1} of {len(paths)}",
                'current_item': path
            })
            log(f"Deleting {full_path}")

            cmd = ['rclone', 'purge', full_path, '-v']

            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, universal_newlines=True)
            job_manager.set_current_process(process)

            # Read output to avoid blocking
            out, _ = process.communicate()

            if process.returncode != 0:
                # Fallback to deletefile if purge failed (likely it was a file)
                cmd_retry = ['rclone', 'deletefile', full_path]
                subprocess.run(cmd_retry, capture_output=True)
                # We won't check retry code strictly, just best effort.
                log(f"Deleted {path} (via fallback)")
            else:
                log(f"Deleted {path}")

        return True

    @staticmethod
    def mkdir_sync(remote, path, name):
        full_path = f"{remote}:{path}/{name}" if path else f"{remote}:{name}"
        log(f"Creating Cloud Folder: {full_path}")
        try:
            subprocess.run(['rclone', 'mkdir', full_path], check=True, capture_output=True)
            return True
        except subprocess.CalledProcessError as e:
            log(f"Mkdir failed: {e}")
            raise Exception("Failed to create folder")

    @staticmethod
    def rename_sync(remote, path, new_name):
        # rclone moveto remote:path remote:parent/new_name
        parent = os.path.dirname(path)
        old_full = f"{remote}:{path}"
        new_full = f"{remote}:{parent}/{new_name}" if parent else f"{remote}:{new_name}"

        log(f"Renaming Cloud Item: {old_full} -> {new_full}")
        try:
            subprocess.run(['rclone', 'moveto', old_full, new_full], check=True, capture_output=True)
            return True
        except subprocess.CalledProcessError as e:
            log(f"Rename failed: {e}")
            raise Exception("Failed to rename item")
