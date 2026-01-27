import os
import uuid
import json
import shutil
from datetime import datetime
from app.core.job_manager import log
import random

class ObfuscationManager:
    """
    Handles the "Camouflage" strategy for Cold Storage.
    Renames archive parts to look like system logs and generates restore maps.
    """

    MAPS_DIR = os.path.join(os.environ.get('DOWNLOAD_ROOT', '/data/downloads'), 'maps')

    @staticmethod
    def generate_boring_metadata(mode='log_rotation'):
        """
        Generates realistic, boring release metadata based on templates.
        Modes: 'log_rotation' (default), 'crash_dump', 'infrastructure'
        """
        date_str = datetime.now().strftime('%Y-%m-%d')
        # Random Build ID (1000-9999)
        build_id = random.randint(1000, 9999)

        # Template 1: Log Rotation (Safest)
        if mode == 'log_rotation':
            tag = f"v{date_str}-logs-{build_id}"
            title = f"System Log Rotation: {date_str} (Build {build_id})"
            body = f"""Automated archival of server logs for node-us-east-{random.randint(1,9)}.
Compression: Raw/Binary
Retention Policy: 90 Days
Status: Verified
Build ID: {build_id}

Warning: These files are encrypted for security compliance. Do not attempt to parse without the decryption key."""

        # Template 2: Crash Dump
        elif mode == 'crash_dump':
            tag = f"dump-build-{build_id}"
            title = f"Core Dump Analysis - Incident #{random.randint(100,999)}"
            body = f"""Memory dump and heap snapshots captured during load testing.
Artifacts split for easier transport.

Contains:
- Kernel traces
- Heap allocation maps
- Binary core dumps (sanitized)

Hash verification passed."""

        # Template 3: Infrastructure
        elif mode == 'infrastructure':
            tag = f"snapshot-v1.{random.randint(4,9)}.{random.randint(0,10)}"
            title = f"Weekly Infrastructure Snapshot (Encrypted)"
            body = f"""Full incremental snapshot of the production cluster.

Type: Cold Storage
Encryption: AES-256
Chunk Size: 1024MB

This release is generated automatically by the backup-daemon. Please do not modify assets manually."""

        else:
            # Fallback
            tag = f"backup-{date_str}-{build_id}"
            title = f"Backup {date_str}"
            body = "Automated backup."

        return {'tag': tag, 'title': title, 'body': body}

    @staticmethod
    def camouflage_files(file_paths):
        """
        Renames files to `sys_log_[DATE]_shard_[UUID].dat`.
        Returns:
            new_paths (list): List of absolute paths to the renamed files.
            mapping (dict): { 'fake_name.dat': 'original_name.rar' }
        """
        if not os.path.exists(ObfuscationManager.MAPS_DIR):
            os.makedirs(ObfuscationManager.MAPS_DIR, exist_ok=True)

        new_paths = []
        mapping = {}

        date_str = datetime.now().strftime("%Y%m%d")

        log(f"🛡️ Starting Camouflage for {len(file_paths)} files...")

        for original_path in file_paths:
            if not os.path.exists(original_path):
                continue

            directory = os.path.dirname(original_path)
            original_name = os.path.basename(original_path)

            # Generate Camouflage Name
            # Pattern: sys_log_20240101_shard_a1b2c3d4.dat
            unique_id = str(uuid.uuid4())[:8]
            fake_name = f"sys_log_{date_str}_shard_{unique_id}.dat"
            fake_path = os.path.join(directory, fake_name)

            try:
                os.rename(original_path, fake_path)
                new_paths.append(fake_path)
                mapping[fake_name] = original_name
                log(f"   🎭 Masked: {original_name} -> {fake_name}")
            except Exception as e:
                log(f"   ❌ Failed to mask {original_name}: {e}")
                # Keep original if failed
                new_paths.append(original_path)

        return new_paths, mapping

    @staticmethod
    def save_map_file(mapping, job_name):
        """
        Saves the mapping dictionary to a text file in data/maps/.
        Format: FAKE_NAME | REAL_NAME
        """
        if not mapping:
            return None

        filename = f"restore_map_{job_name}_{datetime.now().strftime('%H%M%S')}.txt"
        path = os.path.join(ObfuscationManager.MAPS_DIR, filename)

        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(f"# ParFix Cold Storage Map - {job_name}\n")
                f.write(f"# Created: {datetime.now().isoformat()}\n")
                f.write("# DO NOT UPLOAD THIS FILE TO PUBLIC CLOUD\n\n")
                for fake, real in mapping.items():
                    f.write(f"{fake} | {real}\n")

            log(f"🗺️  Restore Map saved: {filename}")
            return path
        except Exception as e:
            log(f"❌ Failed to save map file: {e}")
            return None

    @staticmethod
    def restore_from_dict(mapping, target_dir):
        """
        Restores files using a dictionary mapping {fake: real}.
        """
        if not mapping:
            return False, "Empty mapping provided"

        log(f"♻️  Restoring {len(mapping)} files in {target_dir}")
        count = 0
        try:
            for fake, real in mapping.items():
                fake_path = os.path.join(target_dir, fake)
                real_path = os.path.join(target_dir, real)

                # Check if already restored (real exists, fake doesn't)
                if os.path.exists(real_path) and not os.path.exists(fake_path):
                    continue

                if os.path.exists(fake_path):
                    try:
                        os.rename(fake_path, real_path)
                        count += 1
                        log(f"   ✨ Restored: {real}")
                    except Exception as ex:
                        log(f"   ❌ Failed to restore {fake}: {ex}")

            return True, f"Restored {count} files."
        except Exception as e:
            return False, str(e)

    @staticmethod
    def restore_from_map(map_path, target_dir):
        """
        Restores files using a map file.
        """
        if not os.path.exists(map_path):
            return False, "Map file not found"

        log(f"♻️  Restoring from map: {map_path}")
        mapping = {}
        try:
            with open(map_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.startswith('#') or not line.strip(): continue

                    parts = line.strip().split('|')
                    if len(parts) != 2: continue

                    fake = parts[0].strip()
                    real = parts[1].strip()
                    mapping[fake] = real

            return ObfuscationManager.restore_from_dict(mapping, target_dir)
        except Exception as e:
            return False, str(e)
