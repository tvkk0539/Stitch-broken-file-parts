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
        elif filename.endswith(('.mkv', '.mp4', '.avi', '.mov', '.ts', '.m2ts')):
            return InspectorManager._inspect_media(path)
        elif filename.endswith(('.mp3', '.flac', '.wav', '.m4a', '.aac', '.ogg', '.wma', '.opus', '.alac', '.aiff')):
            return InspectorManager._inspect_audio(path)
        elif filename.endswith(('.jpg', '.jpeg', '.png', '.webp', '.bmp', '.gif', '.tiff', '.tif', '.heic')):
            return InspectorManager._inspect_image(path)
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

                        raw_size = track.get('FileSize')
                        raw_dur = track.get('Duration')

                        # Heuristic: Fix Duration if likely in seconds
                        # Some versions/files return seconds (e.g. 1889.5) instead of MS (1889500)
                        if raw_dur and raw_size:
                            try:
                                d = float(raw_dur)
                                s = float(raw_size)
                                # Try to get bitrate from General track to validate
                                br = float(track.get('OverallBitRate') or track.get('BitRate') or 0)

                                is_seconds = False

                                # Method 1: Cross-check with Bitrate
                                if br > 0:
                                    expected_sec = (s * 8) / br
                                    # If d is close to expected_sec (ratio ~1), it's seconds
                                    if 0.1 < (d / expected_sec) < 10.0:
                                        is_seconds = True
                                    # If d is close to expected_sec * 1000 (ratio ~1000), it's MS

                                # Method 2: Fallback Sanity Check (Max Bitrate)
                                if not is_seconds and br == 0 and d > 0:
                                    # If treated as MS, implied bitrate
                                    dur_s = d / 1000.0
                                    implied_bps = (s * 8) / dur_s
                                    # If > 1 Gbps and Size > 10MB, assume seconds (AVC/HEVC rarely > 1Gbps)
                                    if implied_bps > 1_000_000_000 and s > 10_000_000:
                                        is_seconds = True

                                if is_seconds:
                                    raw_dur = str(d * 1000)
                            except:
                                pass

                        # Duration (Prefer String -> Fallback to Raw + Format)
                        dur = track.get('Duration_String4') or track.get('Duration_String3') or track.get('Duration_String') or track.get('Duration_String1')
                        if not dur:
                            dur = InspectorManager._format_duration(raw_dur) if raw_dur else 'Unknown'
                        info['details'].append(('Duration', dur))

                        # Size (Prefer String -> Fallback to Raw + Format)
                        size = track.get('FileSize_String4') or track.get('FileSize_String3') or track.get('FileSize_String') or track.get('FileSize_String1')
                        if not size:
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
    def _inspect_audio(path):
        try:
            # Run mediainfo with JSON output
            cmd = ['mediainfo', '--Output=JSON', path]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                return {'error': 'MediaInfo failed'}

            data = json.loads(result.stdout)

            # Parse simplified info
            info = {'type': 'audio', 'details': []}

            # Helper to find specific track
            def find_track(type_name):
                if 'media' in data and 'track' in data['media']:
                    for t in data['media']['track']:
                        if t['@type'] == type_name:
                            return t
                return None

            # Get General info first
            general = find_track('General')
            size = 'Unknown'
            dur = 'Unknown'
            if general:
                # Size
                size = general.get('FileSize_String4') or general.get('FileSize_String')
                if not size:
                    raw = general.get('FileSize')
                    if raw: size = InspectorManager._format_size(raw)

                # Duration
                dur = general.get('Duration_String4') or general.get('Duration_String3') or general.get('Duration_String')
                if not dur:
                    raw_dur = general.get('Duration')
                    if raw_dur: dur = InspectorManager._format_duration(raw_dur)

            # Get Audio info
            audio = find_track('Audio')
            if audio:
                # Format
                fmt = audio.get('Format', 'Unknown')
                if audio.get('Format_Profile'):
                    fmt += f" {audio.get('Format_Profile')}"
                info['details'].append(('Format', fmt))

                # Channels
                ch = audio.get('Channel(s)_String') or audio.get('Channel(s)')
                if ch:
                    if str(ch).isdigit(): ch = f"{ch} channels"
                    info['details'].append(('Channels', ch))

                # Sampling Rate
                sr = audio.get('SamplingRate_String') or audio.get('SamplingRate')
                if sr:
                    if str(sr).isdigit(): sr = f"{int(sr)/1000} kHz"
                    info['details'].append(('Sample Rate', sr))

                # Bit Depth
                bd = audio.get('BitDepth_String') or audio.get('BitDepth')
                if bd:
                    if str(bd).isdigit(): bd = f"{bd}-bit"
                    info['details'].append(('Bit Depth', bd))

                # Bitrate
                br = audio.get('BitRate_String') or audio.get('BitRate')
                mode = audio.get('BitRate_Mode')
                if br:
                     if str(br).isdigit(): br = InspectorManager._format_bitrate(br)
                     if mode: br += f" ({mode})"
                     info['details'].append(('Bitrate', br))

                # Compression
                comp = audio.get('Compression_Mode')
                if comp:
                    info['details'].append(('Compression', comp))

            # Add Duration and Size at the end
            if dur != 'Unknown': info['details'].append(('Duration', dur))
            if size != 'Unknown': info['details'].append(('Size', size))

            return info
        except Exception as e:
            return {'error': str(e)}

    @staticmethod
    def _inspect_image(path):
        try:
            # Run mediainfo with JSON output
            cmd = ['mediainfo', '--Output=JSON', path]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                return {'error': 'MediaInfo failed'}

            data = json.loads(result.stdout)

            # Parse simplified info
            info = {'type': 'image', 'details': []}

            # Helper to find specific track
            def find_track(type_name):
                if 'media' in data and 'track' in data['media']:
                    for t in data['media']['track']:
                        if t['@type'] == type_name:
                            return t
                return None

            # Get General info first (for FileSize)
            general = find_track('General')
            size = 'Unknown'
            if general:
                size = general.get('FileSize_String4') or general.get('FileSize_String')
                if not size:
                    raw = general.get('FileSize')
                    if raw: size = InspectorManager._format_size(raw)

            # Get Image info
            image = find_track('Image')
            if image:
                # Format
                fmt = image.get('Format', 'Unknown')
                if image.get('Format_Version'):
                    fmt += f" {image.get('Format_Version')}"
                info['details'].append(('Format', fmt))

                # Resolution
                w = image.get('Width', '?')
                h = image.get('Height', '?')
                info['details'].append(('Resolution', f"{w}x{h}"))

                # Color Space / Chroma
                cs = image.get('ColorSpace')
                chroma = image.get('ChromaSubsampling')
                if cs:
                    line = cs
                    if chroma: line += f" {chroma}"
                    info['details'].append(('Color', line))

                # Bit Depth
                bd = image.get('BitDepth')
                if bd:
                    if str(bd).isdigit(): bd = f"{bd}-bit"
                    info['details'].append(('Bit Depth', bd))

                # Compression
                comp = image.get('Compression_Mode')
                if comp:
                    info['details'].append(('Compression', comp))

            # Add Size (General has priority, but check Image track fallback if General failed)
            if size == 'Unknown' and image:
                s = image.get('FileSize_String4') or image.get('FileSize_String')
                if not s:
                    r = image.get('FileSize')
                    if r: s = InspectorManager._format_size(r)
                if s: size = s

            info['details'].append(('Size', size))

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
