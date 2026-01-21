from app.core.job_manager import log, job_manager
from app.managers.notification import NotificationManager
from app.managers.rclone import RcloneManager
import os
import subprocess
import glob

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

        job_manager.update_job_details({
            'action': f"Creating Archive ({fmt.upper()})",
            'archive_name': archive_name
        })

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
                    job_manager.update_job_details({'error': f"Archiving failed (Code {process.returncode})"})
                    NotificationManager.send_notification(f"❌ ParFix: Archiving Failed for {archive_name}")
                return

            log("Archive created successfully.")
            generated_files = []

            if job_manager.is_cancelled(): return

            # --- PHASE 2: PAR2 GENERATION ---
            if create_par2:
                log("Starting PAR2 Generation...")
                par2_base = archive_name + ".par2"

                job_manager.update_job_details({'action': 'Generating PAR2 Recovery Files'})

                # Determine what files to protect
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
                job_manager.update_job_details({'action': f'Uploading {len(generated_files)} files to Cloud'})
                RcloneManager.run_upload(generated_files, remote, upload_path)
                NotificationManager.send_notification(f"✅ ParFix: Packed & Uploaded {archive_name}")
            else:
                NotificationManager.send_notification(f"✅ ParFix: Packing Complete for {archive_name}")

        except Exception as e:
            log(f"Error during archiving: {str(e)}")
            job_manager.update_job_details({'error': str(e)})
