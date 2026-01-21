from app.core.job_manager import log
import subprocess
import json
import os
import re

class InspectorManager:
    @staticmethod
    def inspect_item(path):
        """
        Inspects a file and returns details.
        - If Archive: Returns contents.
        - If Media: Returns metadata.
        """
        if not os.path.exists(path):
            return {'error': 'File not found'}

        filename = os.path.basename(path).lower()

        if filename.endswith('.rar') or filename.endswith('.7z') or filename.endswith('.001'):
            return InspectorManager._inspect_archive(path)
        elif filename.endswith(('.mkv', '.mp4', '.avi', '.mov', '.ts')):
            return InspectorManager._inspect_media(path)
        else:
            return {'type': 'unknown', 'info': 'No deep inspection available for this file type.'}

    @staticmethod
    def _format_size(size_str):
        try:
            size = float(size_str)
            for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
                if size < 1024:
                    return f"{size:.2f} {unit}"
                size /= 1024
            return f"{size:.2f} PB"
        except (ValueError, TypeError):
            return size_str

    @staticmethod
    def _format_duration(dur_str):
        try:
            # Duration is usually in milliseconds
            ms = float(dur_str)
            seconds = int((ms / 1000) % 60)
            minutes = int((ms / (1000 * 60)) % 60)
            hours = int((ms / (1000 * 60 * 60)))

            parts = []
            if hours > 0: parts.append(f"{hours}h")
            if minutes > 0: parts.append(f"{minutes}m")
            if seconds > 0 or not parts: parts.append(f"{seconds}s")

            return " ".join(parts)
        except (ValueError, TypeError):
            return dur_str

    @staticmethod
    def _format_bitrate(bps_str):
        try:
            # Bitrate is in bits/sec
            bps = float(bps_str)
            if bps >= 1_000_000:
                return f"{bps/1_000_000:.1f} Mb/s"
            elif bps >= 1_000:
                return f"{bps/1_000:.0f} Kb/s"
            return f"{bps:.0f} bps"
        except (ValueError, TypeError):
            return bps_str

    @staticmethod
    def _inspect_media(path):
        try:
            # Run mediainfo with JSON output
            cmd = ['mediainfo', '--Output=JSON', path]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                return {'error': 'MediaInfo failed'}

            data = json.loads(result.stdout)

            # Parse simplified info
            info = {'type': 'media', 'details': []}

            if 'media' in data and 'track' in data['media']:
                for track in data['media']['track']:
                    if track['@type'] == 'General':
                        # Format
                        info['details'].append(('Format', track.get('Format', 'Unknown')))

                        # Duration (Prefer String -> Fallback to Raw + Format)
                        dur = track.get('Duration_String4') or track.get('Duration_String3') or track.get('Duration_String') or track.get('Duration_String1')
                        if not dur:
                            raw_dur = track.get('Duration')
                            dur = InspectorManager._format_duration(raw_dur) if raw_dur else 'Unknown'
                        info['details'].append(('Duration', dur))

                        # Size (Prefer String -> Fallback to Raw + Format)
                        size = track.get('FileSize_String4') or track.get('FileSize_String3') or track.get('FileSize_String') or track.get('FileSize_String1')
                        if not size:
                            raw_size = track.get('FileSize')
                            size = InspectorManager._format_size(raw_size) if raw_size else 'Unknown'
                        info['details'].append(('Size', size))

                    elif track['@type'] == 'Video':
                        res = f"{track.get('Width', '?')}x{track.get('Height', '?')}"
                        fmt_line = f"{track.get('Format', 'Unknown')} ({res})"

                        # Bit Depth (8-bit, 10-bit)
                        bit_depth = track.get('BitDepth_String') or track.get('BitDepth')
                        if bit_depth:
                            # If it's just a number, append 'bit'
                            if str(bit_depth).isdigit():
                                bit_depth = f"{bit_depth}-bit"
                            fmt_line += f" {bit_depth}"

                        info['details'].append(('Video', fmt_line))

                        # Bitrate
                        bitrate = track.get('BitRate_String')
                        if not bitrate:
                            raw_br = track.get('BitRate')
                            bitrate = InspectorManager._format_bitrate(raw_br) if raw_br else 'Unknown'

                        info['details'].append(('Bitrate', bitrate))

                    elif track['@type'] == 'Audio':
                        fmt = track.get('Format', 'Unknown')
                        ch = track.get('Channel(s)_String', '')
                        if not ch:
                            ch = track.get('Channel(s)', '')
                        info['details'].append(('Audio', f"{fmt} {ch}".strip()))

            return info
        except Exception as e:
            return {'error': str(e)}

    @staticmethod
    def _inspect_archive(path):
        try:
            # Try 7z l (works for rar too usually)
            cmd = ['7z', 'l', '-ba', path]
            result = subprocess.run(cmd, capture_output=True, text=True)

            contents = []
            for line in result.stdout.splitlines():
                # 7z list format: Date Time Attr Size Compressed Name
                # We just want Name and Size roughly.
                parts = line.strip().split(maxsplit=5)
                if len(parts) > 5:
                    size = parts[3]
                    name = parts[5]
                    contents.append({'name': name, 'size': size})

            return {
                'type': 'archive',
                'details': [('File Count', len(contents))],
                'contents': contents
            }
        except Exception as e:
            return {'error': str(e)}
