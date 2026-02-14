import os
import subprocess
import logging
import json
from app.core.job_manager import log, job_manager

logger = logging.getLogger(__name__)

class MediaManager:
    """
    Manages media-specific operations: Cover Extraction, Stream Analysis, Stream Extraction.
    """

    AUDIO_EXTENSIONS = {'.mp3', '.flac', '.m4a', '.ogg', '.opus', '.wma', '.m4b', '.wav', '.aiff'}

    @staticmethod
    def get_stream_info(path):
        """
        Uses ffprobe to return detailed stream info.
        Returns: list of dicts.
        """
        try:
            cmd = [
                'ffprobe', '-v', 'quiet', '-print_format', 'json',
                '-show_streams', '-show_format', path
            ]
            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode != 0:
                return {'error': 'ffprobe failed'}

            data = json.loads(res.stdout)
            streams = []

            for s in data.get('streams', []):
                stype = s.get('codec_type')
                if stype not in ['video', 'audio', 'subtitle']: continue

                tags = s.get('tags', {})
                lang = tags.get('language', 'und')
                title = tags.get('title', '')

                info = {
                    'index': s.get('index'),
                    'type': stype,
                    'codec': s.get('codec_name', 'unknown'),
                    'lang': lang,
                    'title': title,
                    'channels': s.get('channels'), # Audio only
                    'width': s.get('width'), # Video only
                    'height': s.get('height') # Video only
                }
                streams.append(info)

            return {'streams': streams, 'format': data.get('format', {})}
        except Exception as e:
            return {'error': str(e)}

    @staticmethod
    def run_extract_streams_job(path, selections):
        """
        Extracts selected streams to separate files.
        selections: list of {index, type, codec, lang}
        """
        log(f"Starting Stream Extraction for: {os.path.basename(path)}")
        job_manager.update_job_details({'action': 'Initializing Extraction...'})

        base_dir = os.path.dirname(path)
        base_name = os.path.splitext(os.path.basename(path))[0]

        # Build FFmpeg command
        # ffmpeg -i input.mkv -map 0:1 -c copy output.aac -map 0:2 -c copy output.srt ...
        cmd = ['ffmpeg', '-y', '-i', path]

        output_files = []

        for sel in selections:
            idx = sel['index']
            stype = sel['type']
            codec = sel['codec']
            lang = sel.get('lang', 'und')

            # Determine extension
            ext = 'dat'
            if stype == 'subtitle':
                if 'subrip' in codec or 'srt' in codec: ext = 'srt'
                elif 'ass' in codec: ext = 'ass'
                elif 'webvtt' in codec: ext = 'vtt'
                elif 'pgs' in codec: ext = 'sup'
                else: ext = 'srt' # Try default container
            elif stype == 'audio':
                if 'aac' in codec: ext = 'aac' # or m4a
                elif 'ac3' in codec: ext = 'ac3'
                elif 'eac3' in codec: ext = 'eac3'
                elif 'mp3' in codec: ext = 'mp3'
                elif 'flac' in codec: ext = 'flac'
                elif 'opus' in codec: ext = 'opus'
                elif 'vorbis' in codec: ext = 'ogg'
                else: ext = 'mka' # Generic Audio container
            elif stype == 'video':
                ext = 'mkv' # Always safe for video streams

            # Construct Output Filename: Name.Lang.TrackID.Ext
            # e.g. Movie.eng.2.aac
            # Sanitize language to prevent path traversal
            safe_lang = "".join([c for c in lang if c.isalnum() or c in ('-', '_')])
            if not safe_lang: safe_lang = 'und'

            out_name = f"{base_name}.{safe_lang}.track{idx}.{ext}"
            out_path = os.path.join(base_dir, out_name)
            output_files.append(out_name)

            cmd.extend(['-map', f"0:{idx}", '-c', 'copy', out_path])

        log(f"Extracting {len(selections)} streams...")
        job_manager.update_job_details({'action': f"Extracting {len(selections)} streams", 'targets': output_files})

        try:
            if job_manager.is_cancelled(): return

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                universal_newlines=True,
                preexec_fn=os.setsid # Create new process group for safe cancellation
            )
            job_manager.set_current_process(process)

            for line in process.stdout:
                # FFmpeg output is noisy, we can filter or just log progress
                if "size=" in line and "time=" in line:
                    # Update progress? FFmpeg outputs to stderr usually, but we merged.
                    pass

            process.wait()

            if process.returncode == 0:
                log(f"Extraction Complete. Created: {', '.join(output_files)}")
            else:
                log(f"Extraction Failed (Code {process.returncode})")
                job_manager.update_job_details({'error': 'FFmpeg Failed'})

        except Exception as e:
            log(f"Extraction Error: {e}")
            job_manager.update_job_details({'error': str(e)})

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
