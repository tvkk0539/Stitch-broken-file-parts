from app.core.job_manager import log, job_manager
from app.managers.notification import NotificationManager
import os
import subprocess
import re
import glob

class RepairManager:
    @staticmethod
    def run_repair_job(directory, forced_par2=None):
        log(f"Starting repair in: {directory}")

        job_manager.update_job_details({
            'action': 'Initializing Repair...',
            'directory': directory
        })

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

            job_manager.update_job_details({'action': 'Running PAR2 Repair/Verify'})

            # Step 2: Wildcard Repair
            all_files = glob.glob(os.path.join(directory, '*'))
            all_files = [os.path.basename(f) for f in all_files]

            cmd = ['par2', 'r', master_par2] + all_files

            process = subprocess.Popen(
                cmd,
                cwd=directory,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
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
                     job_manager.update_job_details({'error': f"PAR2 Repair failed (Code {process.returncode})"})
                     NotificationManager.send_notification(f"❌ ParFix: Repair Failed")
                 return

            log("PAR2 Repair success.")

            if job_manager.is_cancelled(): return

            # Step 3: Extract
            job_manager.update_job_details({'action': 'Extracting Archive...'})
            if RepairManager.extract_archive(directory):
                NotificationManager.send_notification(f"✅ ParFix: Repair & Extract Complete")
            else:
                if job_manager.is_cancelled(): return
                # Rename and retry
                job_manager.update_job_details({'action': 'Renaming and Retrying Extraction...'})
                RepairManager.cleanup_and_rename(directory, master_par2)
                if RepairManager.extract_archive(directory):
                    NotificationManager.send_notification(f"✅ ParFix: Repair & Extract Complete (Retry)")
                else:
                    NotificationManager.send_notification(f"❌ ParFix: Extraction Failed")

        except Exception as e:
            log(f"Error: {str(e)}")
            job_manager.update_job_details({'error': str(e)})

    @staticmethod
    def cleanup_and_rename(directory, master_par2_name):
        log("Renaming phase...")
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
            stdin=subprocess.DEVNULL,
            universal_newlines=True
        )
        job_manager.set_current_process(process)

        for line in process.stdout:
            if "All OK" in line: log("Unrar OK")

        process.wait()
        return process.returncode == 0
