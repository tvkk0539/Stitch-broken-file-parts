import os
import subprocess
import logging
from app.core.job_manager import log

logger = logging.getLogger(__name__)

class MediaManager:
    """
    Manages media-specific operations like Cover Extraction.
    """

    AUDIO_EXTENSIONS = {'.mp3', '.flac', '.m4a', '.ogg', '.opus', '.wma', '.m4b', '.wav', '.aiff'}

    @staticmethod
    def run_extract_covers_job(paths, job_id=None):
        """
        Job to extract cover art from audio files.
        paths: List of absolute paths (files or directories).
        """
        log(f"Starting Cover Extraction for {len(paths)} items...")

        count_success = 0
        count_skipped = 0
        count_failed = 0
        total_files_scanned = 0

        def process_file(file_path):
            nonlocal count_success, count_skipped, count_failed

            # check extension
            _, ext = os.path.splitext(file_path)
            if ext.lower() not in MediaManager.AUDIO_EXTENSIONS:
                return

            # Determine output path
            # "individual files should be file name .jpg" -> /path/song.mp3 -> /path/song.jpg
            base_name = os.path.splitext(os.path.basename(file_path))[0]
            dir_name = os.path.dirname(file_path)
            output_path = os.path.join(dir_name, f"{base_name}.jpg")

            if os.path.exists(output_path):
                # "If the cover is already there skip it don't overwrite"
                # log(f"Skipping {base_name} (Cover exists)") # Verbose log?
                count_skipped += 1
                return

            try:
                # Run ffmpeg
                # -i input -an (no audio) -v (video only, cover is video stream) output.jpg
                # We use -y (overwrite) just in case, but we checked exists above.
                # Adding -nostdin to prevent ffmpeg from reading stdin
                cmd = ['ffmpeg', '-nostdin', '-i', file_path, '-an', output_path]

                # Capture output to avoid spamming logs, check return code
                res = subprocess.run(cmd, capture_output=True, text=True)

                if res.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                    log(f"Extracted: {base_name}.jpg")
                    count_success += 1
                else:
                    # Often fails if no cover exists. This is expected for many files.
                    # We won't log every failure to avoid noise, unless it's a real error.
                    # log(f"No cover found in {base_name}")
                    count_failed += 1

            except Exception as e:
                log(f"Error processing {base_name}: {e}")
                count_failed += 1

        for path in paths:
            if not os.path.exists(path):
                log(f"Path not found: {path}")
                continue

            if os.path.isfile(path):
                total_files_scanned += 1
                process_file(path)
            elif os.path.isdir(path):
                # Deep scan
                for root, dirs, files in os.walk(path):
                    for name in files:
                        total_files_scanned += 1
                        process_file(os.path.join(root, name))

        log(f"Job Complete. Scanned: {total_files_scanned}. Extracted: {count_success}. Skipped: {count_skipped}. No Cover/Failed: {count_failed}.")
