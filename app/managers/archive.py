from app.core.job_manager import log, job_manager
from app.managers.notification import NotificationManager
from app.managers.rclone import RcloneManager
import os
import subprocess
import glob
import re

class ArchiveManager:
    @staticmethod
    def run_archive_job(source_path, archive_name, split_size, password, fmt='rar', create_par2=True, upload=False, remote=None, upload_path='', naming_scheme='part1', rar_recovery_record=True):
        parent_dir = os.path.dirname(source_path)
        base_name = os.path.basename(source_path)

        # 1. Clean the name (remove extensions)
        clean_name = archive_name
        if clean_name.lower().endswith('.rar'): clean_name = clean_name[:-4]
        elif clean_name.lower().endswith('.7z'): clean_name = clean_name[:-3]

        # 2. Construct Output Name based on Scheme
        if fmt == 'rar':
            if naming_scheme == 'part001':
                archive_name = f"{clean_name}.part001.rar"
            elif naming_scheme == 'part01':
                archive_name = f"{clean_name}.part01.rar"
            else:
                archive_name = f"{clean_name}.rar"
        else:
            archive_name = f"{clean_name}.7z"

        log(f"Packing '{base_name}' into '{archive_name}' ({fmt})")

        job_manager.update_job_details({
            'action': f"Creating Archive ({fmt.upper()})",
            'archive_name': archive_name
        })

        cmd = []
        if fmt == 'rar':
            # -y: Assume Yes on questions (overwrite, etc)
            cmd = ['rar', 'a', '-m0', '-y', f'-v{split_size}', '-ep1']
            if rar_recovery_record:
                cmd.append('-rr5p')
            if password:
                cmd.append(f'-hp{password}')
            cmd.append(archive_name)
            cmd.append(source_path)
        else:
            size_arg = split_size.lower().replace('m', 'm').replace('g', 'g')
            # -y: Assume Yes
            cmd = ['7z', 'a', f'-v{size_arg}', '-mx0', '-y']
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
                # Recalculate clean_name for safety in case local vars drifted (though they haven't)
                clean_name = archive_name
                if clean_name.lower().endswith('.rar'):
                    # Handle .part001.rar case to get base
                    if re.search(r'\.part\d+\.rar$', clean_name, re.IGNORECASE):
                        clean_name = re.sub(r'\.part\d+\.rar$', '', clean_name, flags=re.IGNORECASE)
                    elif clean_name.lower().endswith('.rar'):
                        clean_name = clean_name[:-4]

                target_pattern = f"{clean_name}.part*.rar" if fmt == 'rar' else archive_name + ".*"

                # If target pattern didn't match anything, maybe it wasn't split?
                # Try simple wildcard
                files_to_protect = glob.glob(os.path.join(parent_dir, target_pattern))
                if fmt == 'rar' and not files_to_protect:
                     # Fallback for non-split RARs
                     files_to_protect = glob.glob(os.path.join(parent_dir, f"{clean_name}.rar"))
                if fmt == '7z' and not files_to_protect and os.path.exists(os.path.join(parent_dir, archive_name)):
                     files_to_protect = [os.path.join(parent_dir, archive_name)]

                if files_to_protect:
                    files_to_protect.sort()
                    generated_files.extend(files_to_protect)

                    # -q: Quiet (No prompts)
                    par2_cmd = ['par2', 'c', '-q', '-r10', par2_base] + [os.path.basename(f) for f in files_to_protect]

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

    @staticmethod
    def run_compress_job(source_path, name, fmt, level, password=None):
        parent_dir = os.path.dirname(source_path)
        base_name = os.path.basename(source_path)

        # Ensure correct extension
        # If user typed "MyFile.zip", don't add .zip again.
        # But if format is tar.gz, and user typed MyFile, make it MyFile.tar.gz

        # Simple logic: Strip known extension if present, then append correct one
        clean_name = name
        for ext in ['.7z', '.zip', '.tar.gz', '.tar.bz2', '.tar']:
            if clean_name.endswith(ext):
                clean_name = clean_name[:-len(ext)]
                break

        archive_name = f"{clean_name}.{fmt}"

        log(f"Compressing '{base_name}' -> '{archive_name}' (Format: {fmt}, Level: {level})")

        job_manager.update_job_details({
            'action': f"Compressing to {fmt.upper()}",
            'target': archive_name
        })

        cmd = []

        # Use native 'tar' for TAR formats (handles recursion correctly)
        if fmt.startswith('tar'):
            # -c: Create
            # -f: File
            flags = '-cf'
            if 'gz' in fmt: flags = '-czf'
            if 'bz2' in fmt: flags = '-cjf'

            # tar -czf archive.tar.gz -C parent base_name
            # -C is crucial to avoid storing full absolute paths
            cmd = ['tar', flags, archive_name, '-C', parent_dir, base_name]

        else:
            # Use 7-Zip for 7z and Zip
            type_flag = f"-t{fmt}"

            # Level: -mx0 to -mx9
            mx_flag = f"-mx{level}"

            cmd = ['7z', 'a', type_flag, mx_flag, '-y']

            if password and (fmt == '7z' or fmt == 'zip'):
                cmd.append(f'-p{password}')
                if fmt == '7z':
                    cmd.append('-mhe=on') # Encrypt headers for 7z

            cmd.append(archive_name)
            cmd.append(source_path)

        try:
            if job_manager.is_cancelled(): return

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
                if line and ("%" in line or "Creating" in line):
                     log(f"[{fmt.upper()}] {line}")

            process.wait()

            if process.returncode != 0:
                if job_manager.is_cancelled():
                    log("Compression Cancelled")
                else:
                    log(f"Compression failed (Code {process.returncode})")
                    job_manager.update_job_details({'error': f"Failed (Code {process.returncode})"})
                    NotificationManager.send_notification(f"❌ ParFix: Compression Failed for {archive_name}")
            else:
                log("Compression successful.")
                NotificationManager.send_notification(f"✅ ParFix: Compressed {archive_name}")

        except Exception as e:
            log(f"Error during compression: {str(e)}")
            job_manager.update_job_details({'error': str(e)})
