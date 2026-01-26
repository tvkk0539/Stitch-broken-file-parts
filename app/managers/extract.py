from app.core.job_manager import log, job_manager
from app.managers.notification import NotificationManager
import os
import subprocess

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
                # Broaden search for universal format support
                # Prioritize common archive types
                extensions = ('.7z', '.zip', '.rar', '.tar', '.gz', '.bz2', '.xz', '.iso', '.img', '.001')
                for f in files:
                    if f.lower().endswith(extensions):
                        archive_file = f
                        break

        if not archive_file:
            log(f"No archive found for {method}")
            return

        log(f"Extracting {archive_file} ({method})")

        job_manager.update_job_details({
            'action': f"Extracting ({method.upper()})",
            'archive': archive_file
        })

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
                stdin=subprocess.DEVNULL,
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
                    job_manager.update_job_details({'error': f"Extraction failed (Code {process.returncode})"})

        except Exception as e:
            log(f"Extraction Error: {e}")
            job_manager.update_job_details({'error': str(e)})
