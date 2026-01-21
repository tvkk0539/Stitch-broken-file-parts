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
                        info['details'].append(('Format', track.get('Format')))
                        info['details'].append(('Duration', track.get('Duration_String4')))
                        info['details'].append(('Size', track.get('FileSize_String4')))
                    elif track['@type'] == 'Video':
                        res = f"{track.get('Width', '?')}x{track.get('Height', '?')}"
                        info['details'].append(('Video', f"{track.get('Format')} ({res})"))
                        info['details'].append(('Bitrate', track.get('BitRate_String')))
                    elif track['@type'] == 'Audio':
                        info['details'].append(('Audio', f"{track.get('Format')} {track.get('Channel(s)_String', '')}"))

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
