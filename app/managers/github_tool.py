from app.core.job_manager import log, job_manager
from app.managers.notification import NotificationManager
from app.core import config
import requests
import os
import shutil

class GitHubManager:
    @staticmethod
    def get_releases(repo_url):
        """
        Fetches the latest releases for a given repo (e.g., 'radarr/radarr').
        Returns a list of assets from the latest release.
        """
        try:
            # Clean repo string (remove https://github.com/ if present)
            repo = repo_url.replace('https://github.com/', '').strip('/')

            # Helper to get headers (auth optional for public, but good for rate limits)
            conf = config.load_config()
            token = conf.get('github_token')
            headers = {'Accept': 'application/vnd.github.v3+json'}
            if token:
                headers['Authorization'] = f'token {token}'

            # Get Latest Release
            url = f"https://api.github.com/repos/{repo}/releases/latest"
            log(f"Fetching GitHub Release: {url}")

            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code != 200:
                return {'error': f"GitHub API Error: {resp.status_code} {resp.reason}"}

            data = resp.json()

            release_info = {
                'tag': data.get('tag_name'),
                'name': data.get('name'),
                'published_at': data.get('published_at'),
                'assets': []
            }

            for asset in data.get('assets', []):
                release_info['assets'].append({
                    'name': asset['name'],
                    'size': asset['size'],
                    'download_url': asset['browser_download_url']
                })

            return release_info

        except Exception as e:
            log(f"GitHub Error: {e}")
            return {'error': str(e)}

    @staticmethod
    def run_download_job(asset_url, filename, dest_path):
        """
        Background job to download a file from GitHub.
        """
        log(f"Starting GitHub Download: {filename}")
        job_manager.update_job_details({
            'action': f"Downloading {filename}",
            'destination': dest_path
        })

        try:
            # Prepare destination
            if not os.path.exists(dest_path):
                os.makedirs(dest_path, exist_ok=True)

            final_path = os.path.join(dest_path, filename)

            # Stream download
            with requests.get(asset_url, stream=True) as r:
                r.raise_for_status()
                total_size = int(r.headers.get('content-length', 0))
                downloaded = 0

                with open(final_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        if job_manager.is_cancelled():
                            log("Download Cancelled")
                            return # Exit immediately

                        f.write(chunk)
                        downloaded += len(chunk)

                        # Update progress occasionally
                        if total_size > 0:
                            percent = int((downloaded / total_size) * 100)
                            # Only update job details periodically to avoid spamming locks
                            if downloaded % (1024*1024) == 0: # Every 1MB
                                job_manager.update_job_details({'progress': f"{percent}%"})

            log(f"GitHub Download Complete: {filename}")
            NotificationManager.send_notification(f"✅ ParFix: Downloaded {filename} from GitHub")

        except Exception as e:
            log(f"Download Failed: {e}")
            job_manager.update_job_details({'error': str(e)})
            # Cleanup partial file
            if os.path.exists(final_path):
                 try: os.remove(final_path)
                 except: pass

    @staticmethod
    def run_publish_job(repo, tag_name, file_path, token):
        """
        Background job to create a release and upload an asset.
        """
        repo = repo.replace('https://github.com/', '').strip('/')
        filename = os.path.basename(file_path)

        log(f"Starting GitHub Publish: {repo} @ {tag_name}")
        job_manager.update_job_details({'action': 'Creating Release...'})

        if not token:
            job_manager.update_job_details({'error': 'No GitHub Token provided'})
            return

        headers = {
            'Authorization': f'token {token}',
            'Accept': 'application/vnd.github.v3+json'
        }

        try:
            # 1. Create Release
            create_url = f"https://api.github.com/repos/{repo}/releases"
            payload = {
                "tag_name": tag_name,
                "name": f"Release {tag_name}",
                "body": "Uploaded via ParFix Utility",
                "draft": False,
                "prerelease": False
            }

            r = requests.post(create_url, json=payload, headers=headers)
            if r.status_code not in [200, 201]:
                # Maybe tag exists? Try getting it.
                log(f"Release create failed ({r.status_code}), trying to find existing...")
                get_url = f"https://api.github.com/repos/{repo}/releases/tags/{tag_name}"
                r = requests.get(get_url, headers=headers)
                if r.status_code != 200:
                    raise Exception(f"Could not create or find release: {r.text}")

            release_data = r.json()
            upload_url_template = release_data['upload_url'] # e.g. https://uploads.github.com/...{?name,label}
            upload_url = upload_url_template.split('{')[0] + f"?name={filename}"

            # 2. Upload Asset
            job_manager.update_job_details({'action': f'Uploading {filename}...'})
            log(f"Uploading to: {upload_url}")

            if job_manager.is_cancelled(): return

            with open(file_path, 'rb') as f:
                # GitHub requires specific header for uploads
                upload_headers = headers.copy()
                upload_headers['Content-Type'] = 'application/octet-stream'

                ru = requests.post(upload_url, data=f, headers=upload_headers)

                if ru.status_code not in [200, 201]:
                    raise Exception(f"Upload failed: {ru.text}")

            log("GitHub Publish Success")
            NotificationManager.send_notification(f"✅ ParFix: Published {filename} to GitHub ({repo})")

        except Exception as e:
            log(f"Publish Failed: {e}")
            job_manager.update_job_details({'error': str(e)})
