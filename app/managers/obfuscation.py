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
    def generate_boring_metadata(template='log_rotation'):
        """
        Generates realistic, boring release metadata based on templates.
        Templates: 'log_rotation', 'crash_dump', 'infrastructure', 'db_backup', 'ai_weights', 'cdn_cache', 'debug_symbols'
        If 'random' is passed, selects one randomly.
        """
        templates = [
            'log_rotation', 'crash_dump', 'infrastructure', 'db_backup',
            'ai_weights', 'cdn_cache', 'debug_symbols'
        ]

        if template == 'random':
            template = random.choice(templates)

        # Default fallback
        if template not in templates:
            template = 'log_rotation'

        date_str = datetime.now().strftime('%Y-%m-%d')
        build_id = random.randint(1000, 9999)

        tag = ""
        title = ""
        body = ""

        # 1. Log Rotation
        if template == 'log_rotation':
            tag = f"v{date_str}-logs-{build_id}"
            title = f"System Log Rotation: {date_str} (Build {build_id})"
            body = f"""Automated archival of server logs for node-us-east-{random.randint(1,9)}.
Compression: Raw/Binary
Retention Policy: 90 Days
Status: Verified
Build ID: {build_id}

Warning: These files are encrypted for security compliance. Do not attempt to parse without the decryption key."""

        # 2. Crash Dump
        elif template == 'crash_dump':
            tag = f"dump-build-{build_id}"
            title = f"Core Dump Analysis - Incident #{random.randint(100,999)}"
            body = f"""Memory dump and heap snapshots captured during load testing.
Artifacts split for easier transport.

Contains:
- Kernel traces
- Heap allocation maps
- Binary core dumps (sanitized)

Hash verification passed."""

        # 3. Infrastructure
        elif template == 'infrastructure':
            tag = f"snapshot-v1.{random.randint(4,9)}.{random.randint(0,10)}"
            title = f"Weekly Infrastructure Snapshot (Encrypted)"
            body = f"""Full incremental snapshot of the production cluster.

Type: Cold Storage
Encryption: AES-256
Chunk Size: 1024MB

This release is generated automatically by the backup-daemon. Please do not modify assets manually."""

        # 4. Database Backup
        elif template == 'db_backup':
            tag = f"wal-arch-{date_str}-{build_id}"
            title = f"Postgres WAL Archive: {date_str}"
            body = f"""Write-Ahead Log (WAL) segments for partial recovery.
DB Version: 14.2
Cluster ID: cl-{random.randint(1000,9999)}
Compression: LZ4

Warning: Contains transactional data. Access restricted to DBA group."""

        # 5. AI Weights
        elif template == 'ai_weights':
            tag = f"ckpt-epoch-{random.randint(50,200)}-{build_id}"
            title = f"Model Checkpoints (fp16) - Epoch {random.randint(50,200)}"
            body = f"""Intermediate training checkpoints for LLM fine-tuning.
Precision: fp16
Optimizer State: Included
Batch Size: 512

Use `torch.load` with map_location='cpu' for inspection."""

        # 6. CDN Cache
        elif template == 'cdn_cache':
            tag = f"assets-v{random.randint(1,5)}.{random.randint(0,9)}-{build_id}"
            title = f"Static Assets Bundle (Edge Cache)"
            body = f"""Pre-warmed cache dump for region: eu-central-1.
Content-Type: application/octet-stream
TTL: 24h

This bundle is used for cache hydration during cold starts."""

        # 7. Debug Symbols
        elif template == 'debug_symbols':
            tag = f"sym-v{random.randint(10,20)}.{build_id}"
            title = f"DWARF Debug Symbols (Release Build)"
            body = f"""Detached debug symbols for stack trace symbolication.
Platform: Linux x86_64
Compiler: GCC 11.2

Required for gdb/lldb analysis of production binaries."""

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
        found_count = 0
        already_restored_count = 0
        missing_count = 0
        first_missing = None

        try:
            for fake, real in mapping.items():
                fake_path = os.path.join(target_dir, fake)
                real_path = os.path.join(target_dir, real)

                # Check if already restored (real exists, fake doesn't)
                if os.path.exists(real_path) and not os.path.exists(fake_path):
                    already_restored_count += 1
                    continue

                if os.path.exists(fake_path):
                    try:
                        os.rename(fake_path, real_path)
                        found_count += 1
                        log(f"   ✨ Restored: {real}")
                    except Exception as ex:
                        log(f"   ❌ Failed to restore {fake}: {ex}")
                else:
                    missing_count += 1
                    if not first_missing:
                        first_missing = fake

            if found_count == 0 and already_restored_count == 0:
                log(f"⚠️ No matching files found in {target_dir}")
                if first_missing:
                    log(f"   Expected example: {first_missing}")
                return False, f"No files found. Expected e.g. '{first_missing}'"

            msg = f"Restored {found_count} files."
            if already_restored_count > 0:
                msg += f" ({already_restored_count} already restored)"
            if missing_count > 0:
                msg += f" ({missing_count} missing)"

            log(f"✅ {msg}")
            return True, msg

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
