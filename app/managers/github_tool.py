from app.core.job_manager import log, job_manager
from app.managers.notification import NotificationManager
from app.core import config
import requests
import os
import shutil
import subprocess
import base64
from nacl import encoding, public

class GitHubManager:

    # --- Account Management ---

    @staticmethod
    def list_accounts():
        """
        Returns a list of stored accounts from config.
        Checks for legacy 'github_token' and migrates it if found.
        """
        conf = config.load_config()
        accounts = conf.get('github_accounts', [])

        # Migration Check
        legacy_token = conf.get('github_token')
        if legacy_token:
            log("Migrating legacy GitHub token...")
            try:
                # Try to resolve token to user
                acc = GitHubManager._fetch_user_profile(legacy_token)
                if acc:
                    # Check if already exists
                    if not any(a['id'] == acc['id'] for a in accounts):
                        accounts.append(acc)
                        conf['github_accounts'] = accounts
                        conf['github_token'] = None # Remove legacy
                        config.save_config(conf)
                        log(f"Migrated legacy token to account: {acc['username']}")
            except Exception as e:
                log(f"Legacy token migration failed: {e}")

        # Return sanitized list (hide tokens)
        sanitized = []
        for a in accounts:
            sanitized.append({
                'id': a['id'],
                'username': a['username'],
                'avatar_url': a.get('avatar_url', ''),
                'name': a.get('name', '')
            })
        return sanitized

    @staticmethod
    def add_account(token):
        """
        Verifies token with GitHub, fetches profile, and saves to config.
        """
        try:
            profile = GitHubManager._fetch_user_profile(token)
            if not profile:
                return {'error': 'Invalid Token or Network Error'}

            conf = config.load_config()
            accounts = conf.get('github_accounts', [])

            # Remove existing if same ID (Update)
            accounts = [a for a in accounts if a['id'] != profile['id']]

            accounts.append(profile)
            conf['github_accounts'] = accounts
            config.save_config(conf)

            return {'status': 'success', 'username': profile['username']}
        except Exception as e:
            return {'error': str(e)}

    @staticmethod
    def remove_account(account_id):
        conf = config.load_config()
        accounts = conf.get('github_accounts', [])
        new_list = [a for a in accounts if str(a['id']) != str(account_id)]

        if len(new_list) < len(accounts):
            conf['github_accounts'] = new_list
            config.save_config(conf)
            return {'status': 'removed'}
        return {'error': 'Account not found'}

    @staticmethod
    def _fetch_user_profile(token):
        """Helper to get user info from GitHub."""
        headers = {
            'Authorization': f'token {token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        r = requests.get('https://api.github.com/user', headers=headers, timeout=10)
        if r.status_code != 200:
            raise Exception(f"GitHub Auth Failed: {r.status_code}")

        data = r.json()
        return {
            'id': str(data['id']),
            'username': data['login'],
            'name': data.get('name'),
            'avatar_url': data.get('avatar_url'),
            'token': token # Store token securely in config
        }

    @staticmethod
    def _get_token_for_account(account_id):
        conf = config.load_config()
        for a in conf.get('github_accounts', []):
            if str(a['id']) == str(account_id):
                return a['token']
        return None

    # --- Operations ---

    @staticmethod
    def list_user_repos(account_id, type_filter='all'):
        token = GitHubManager._get_token_for_account(account_id)
        if not token:
            return {'error': 'Account token not found'}

        headers = {
            'Authorization': f'token {token}',
            'Accept': 'application/vnd.github.v3+json'
        }

        try:
            # We need to paginate or just get first 100
            url = f"https://api.github.com/user/repos?type={type_filter}&sort=updated&per_page=100"
            r = requests.get(url, headers=headers, timeout=10)
            if r.status_code != 200:
                return {'error': f"Failed to list repos: {r.status_code}"}

            repos = []
            for item in r.json():
                repos.append({
                    'name': item['full_name'],
                    'private': item['private'],
                    'stars': item.get('stargazers_count', 0),
                    'updated_at': item.get('updated_at'),
                    'html_url': item.get('html_url')
                })
            return repos
        except Exception as e:
            return {'error': str(e)}

    @staticmethod
    def update_repo_visibility(repo_name, private, account_id):
        token = GitHubManager._get_token_for_account(account_id)
        if not token:
            return {'error': 'Account token not found'}

        headers = {
            'Authorization': f'token {token}',
            'Accept': 'application/vnd.github.v3+json'
        }

        try:
            url = f"https://api.github.com/repos/{repo_name}"
            payload = {'private': private}
            r = requests.patch(url, json=payload, headers=headers, timeout=10)

            if r.status_code == 200:
                return {'status': 'success', 'private': r.json()['private']}
            else:
                return {'error': f"Failed to update visibility: {r.text}"}
        except Exception as e:
            return {'error': str(e)}

    @staticmethod
    def create_repository(name, private, description, account_id):
        token = GitHubManager._get_token_for_account(account_id)
        if not token: return {'error': 'Auth failed'}

        headers = {
            'Authorization': f'token {token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        payload = {
            'name': name,
            'private': private,
            'description': description or '',
            'auto_init': True # Useful to have README
        }

        try:
            r = requests.post('https://api.github.com/user/repos', json=payload, headers=headers)
            if r.status_code == 201:
                return {'status': 'created', 'repo': r.json()['full_name']}
            return {'error': f"Create failed: {r.text}"}
        except Exception as e:
            return {'error': str(e)}

    @staticmethod
    def rename_repository(owner, repo, new_name, account_id):
        token = GitHubManager._get_token_for_account(account_id)
        if not token: return {'error': 'Auth failed'}

        headers = {
            'Authorization': f'token {token}',
            'Accept': 'application/vnd.github.v3+json'
        }

        try:
            url = f"https://api.github.com/repos/{owner}/{repo}"
            r = requests.patch(url, json={'name': new_name}, headers=headers)
            if r.status_code == 200:
                return {'status': 'renamed'}
            return {'error': f"Rename failed: {r.text}"}
        except Exception as e:
            return {'error': str(e)}

    @staticmethod
    def delete_repository(owner, repo, account_id):
        token = GitHubManager._get_token_for_account(account_id)
        if not token: return {'error': 'Auth failed'}

        headers = {
            'Authorization': f'token {token}',
            'Accept': 'application/vnd.github.v3+json'
        }

        try:
            url = f"https://api.github.com/repos/{owner}/{repo}"
            r = requests.delete(url, headers=headers)
            if r.status_code == 204:
                return {'status': 'deleted'}
            return {'error': f"Delete failed: {r.text}"}
        except Exception as e:
            return {'error': str(e)}

    @staticmethod
    def clone_repository_job(repo_url, dest_path, account_id):
        # We need token to clone private repos
        token = GitHubManager._get_token_for_account(account_id)

        # Inject token into URL for auth: https://oauth2:TOKEN@github.com/...
        if token and 'github.com' in repo_url:
            clean_url = repo_url.replace('https://', '').replace('http://', '')
            auth_url = f"https://oauth2:{token}@{clean_url}"
        else:
            auth_url = repo_url

        log(f"Cloning {repo_url} to {dest_path}")
        job_manager.update_job_details({'action': 'Cloning repository...'})

        try:
            if os.path.exists(dest_path):
                raise Exception("Destination already exists")

            cmd = ['git', 'clone', '--progress', auth_url, dest_path]

            process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True
            )
            job_manager.set_current_process(process)

            for line in process.stdout:
                if "Receiving objects" in line or "Resolving deltas" in line:
                    log(f"[GIT] {line.strip()}")

            process.wait()

            if process.returncode == 0:
                log("Clone successful")
                NotificationManager.send_notification(f"✅ ParFix: Cloned {repo_url}")
            else:
                raise Exception(f"Git clone failed (Code {process.returncode})")

        except Exception as e:
            log(f"Clone error: {e}")
            job_manager.update_job_details({'error': str(e)})

    # --- Actions ---

    @staticmethod
    def list_workflows(repo, account_id):
        token = GitHubManager._get_token_for_account(account_id)
        if not token: return {'error': 'Auth failed'}

        headers = {'Authorization': f'token {token}', 'Accept': 'application/vnd.github.v3+json'}
        try:
            r = requests.get(f"https://api.github.com/repos/{repo}/actions/workflows", headers=headers)
            if r.status_code != 200: return {'error': 'Failed to list workflows'}
            return r.json()['workflows']
        except Exception as e: return {'error': str(e)}

    @staticmethod
    def list_workflow_runs(repo, account_id):
        token = GitHubManager._get_token_for_account(account_id)
        if not token: return {'error': 'Auth failed'}

        headers = {'Authorization': f'token {token}', 'Accept': 'application/vnd.github.v3+json'}
        try:
            r = requests.get(f"https://api.github.com/repos/{repo}/actions/runs?per_page=20", headers=headers)
            if r.status_code != 200: return {'error': 'Failed to list runs'}
            return r.json()['workflow_runs']
        except Exception as e: return {'error': str(e)}

    @staticmethod
    def trigger_workflow(repo, workflow_id, ref, account_id):
        token = GitHubManager._get_token_for_account(account_id)
        headers = {'Authorization': f'token {token}', 'Accept': 'application/vnd.github.v3+json'}
        try:
            url = f"https://api.github.com/repos/{repo}/actions/workflows/{workflow_id}/dispatches"
            r = requests.post(url, json={'ref': ref}, headers=headers)
            if r.status_code == 204: return {'status': 'triggered'}
            return {'error': f"Failed: {r.text}"}
        except Exception as e: return {'error': str(e)}

    @staticmethod
    def cancel_workflow_run(repo, run_id, account_id):
        token = GitHubManager._get_token_for_account(account_id)
        headers = {'Authorization': f'token {token}', 'Accept': 'application/vnd.github.v3+json'}
        try:
            url = f"https://api.github.com/repos/{repo}/actions/runs/{run_id}/cancel"
            requests.post(url, headers=headers)
            return {'status': 'cancelled'}
        except Exception as e: return {'error': str(e)}

    # --- Contents & File Browser ---

    @staticmethod
    def get_branches(owner, repo, account_id):
        token = GitHubManager._get_token_for_account(account_id)
        if not token: return {'error': 'Auth failed'}

        headers = {'Authorization': f'token {token}', 'Accept': 'application/vnd.github.v3+json'}
        try:
            url = f"https://api.github.com/repos/{owner}/{repo}/branches?per_page=100"
            r = requests.get(url, headers=headers)
            if r.status_code != 200: return {'error': f"Failed to list branches: {r.text}"}

            return [b['name'] for b in r.json()]
        except Exception as e: return {'error': str(e)}

    @staticmethod
    def get_contents(owner, repo, path, account_id, branch='main'):
        token = GitHubManager._get_token_for_account(account_id)
        if not token: return {'error': 'Auth failed'}

        headers = {'Authorization': f'token {token}', 'Accept': 'application/vnd.github.v3+json'}
        try:
            # Clean path
            path = path.strip('/')
            url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}?ref={branch}"
            r = requests.get(url, headers=headers)

            if r.status_code != 200:
                 return {'error': f"Failed to fetch contents: {r.status_code}"}

            data = r.json()

            # If it's a list, it's a directory
            if isinstance(data, list):
                items = []
                for item in data:
                    items.append({
                        'name': item['name'],
                        'path': item['path'],
                        'type': item['type'], # 'file' or 'dir'
                        'size': item['size'],
                        'sha': item['sha'],
                        'url': item['html_url']
                    })
                # Sort: dirs first
                items.sort(key=lambda x: (x['type'] != 'dir', x['name'].lower()))
                return {'type': 'dir', 'items': items}

            # If it's a dict, it's a file
            elif isinstance(data, dict):
                 return {
                     'type': 'file',
                     'name': data['name'],
                     'path': data['path'],
                     'size': data['size'],
                     'sha': data['sha'],
                     'content': data.get('content'), # Base64 encoded
                     'encoding': data.get('encoding')
                 }

        except Exception as e: return {'error': str(e)}

    @staticmethod
    def create_update_file(owner, repo, path, content_b64, message, account_id, sha=None, branch='main'):
        """
        Creates or updates a file.
        content_b64: Base64 encoded string of the file content.
        sha: Required if updating an existing file.
        """
        token = GitHubManager._get_token_for_account(account_id)
        if not token: return {'error': 'Auth failed'}

        headers = {'Authorization': f'token {token}', 'Accept': 'application/vnd.github.v3+json'}

        try:
            url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"

            payload = {
                'message': message,
                'content': content_b64,
                'branch': branch
            }
            if sha:
                payload['sha'] = sha

            r = requests.put(url, json=payload, headers=headers)

            if r.status_code in [200, 201]:
                action = "Updated" if sha else "Created"
                return {'status': 'success', 'action': action, 'commit': r.json()['commit']['sha']}
            else:
                return {'error': f"Operation failed: {r.text}"}

        except Exception as e: return {'error': str(e)}

    @staticmethod
    def delete_repo_file(owner, repo, path, sha, message, account_id, branch='main'):
        token = GitHubManager._get_token_for_account(account_id)
        if not token: return {'error': 'Auth failed'}

        headers = {'Authorization': f'token {token}', 'Accept': 'application/vnd.github.v3+json'}

        try:
            url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
            payload = {
                'message': message,
                'sha': sha,
                'branch': branch
            }

            r = requests.delete(url, json=payload, headers=headers)

            if r.status_code == 200:
                return {'status': 'deleted', 'commit': r.json()['commit']['sha']}
            else:
                return {'error': f"Delete failed: {r.text}"}

        except Exception as e: return {'error': str(e)}

    @staticmethod
    def upload_server_file_job(owner, repo, local_path, remote_path, message, branch, account_id):
        """
        Reads a local file and pushes it to GitHub.
        """
        log(f"Starting Upload to GitHub: {local_path} -> {remote_path}")
        job_manager.update_job_details({'action': f"Reading {os.path.basename(local_path)}..."})

        try:
            if not os.path.exists(local_path):
                raise Exception("Local file not found")

            # Check file size (GitHub API limit ~100MB)
            size_mb = os.path.getsize(local_path) / (1024 * 1024)
            if size_mb > 95:
                 raise Exception("File too large for GitHub API (>95MB)")

            # Read file
            with open(local_path, 'rb') as f:
                content = f.read()

            content_b64 = base64.b64encode(content).decode('utf-8')

            # Check if file exists to get SHA (for update)
            # Use get_contents to check
            existing = GitHubManager.get_contents(owner, repo, remote_path, account_id, branch)
            sha = None
            if not isinstance(existing, dict) or 'error' not in existing:
                 # It might exist
                 if isinstance(existing, dict) and existing.get('type') == 'file':
                     sha = existing.get('sha')

            job_manager.update_job_details({'action': "Pushing to GitHub..."})

            res = GitHubManager.create_update_file(
                owner, repo, remote_path, content_b64, message, account_id, sha, branch
            )

            if 'error' in res:
                raise Exception(res['error'])

            log(f"Upload Successful: {res['action']}")
            NotificationManager.send_notification(f"✅ ParFix: Uploaded {os.path.basename(local_path)} to {repo}")

        except Exception as e:
            log(f"GitHub Upload Failed: {e}")
            job_manager.update_job_details({'error': str(e)})

    # --- Secrets ---

    @staticmethod
    def list_secrets(owner, repo, account_id):
        token = GitHubManager._get_token_for_account(account_id)
        if not token: return {'error': 'Auth failed'}

        headers = {'Authorization': f'token {token}', 'Accept': 'application/vnd.github.v3+json'}
        try:
            url = f"https://api.github.com/repos/{owner}/{repo}/actions/secrets"
            r = requests.get(url, headers=headers)
            if r.status_code != 200: return {'error': f"Failed to list secrets: {r.text}"}

            data = r.json()
            return {'total_count': data.get('total_count', 0), 'secrets': data.get('secrets', [])}
        except Exception as e: return {'error': str(e)}

    @staticmethod
    def put_secret(owner, repo, name, value, account_id):
        token = GitHubManager._get_token_for_account(account_id)
        if not token: return {'error': 'Auth failed'}

        headers = {'Authorization': f'token {token}', 'Accept': 'application/vnd.github.v3+json'}

        try:
            # 1. Get Public Key
            key_url = f"https://api.github.com/repos/{owner}/{repo}/actions/secrets/public-key"
            r = requests.get(key_url, headers=headers)
            if r.status_code != 200: return {'error': f"Failed to get public key: {r.text}"}

            key_data = r.json()
            public_key_id = key_data['key_id']
            public_key_val = key_data['key']

            # 2. Encrypt Value
            public_key = public.PublicKey(public_key_val.encode("utf-8"), encoding.Base64Encoder())
            sealed_box = public.SealedBox(public_key)
            encrypted = sealed_box.encrypt(value.encode("utf-8"))
            encrypted_b64 = base64.b64encode(encrypted).decode("utf-8")

            # 3. Put Secret
            put_url = f"https://api.github.com/repos/{owner}/{repo}/actions/secrets/{name}"
            payload = {
                'encrypted_value': encrypted_b64,
                'key_id': public_key_id
            }

            r = requests.put(put_url, json=payload, headers=headers)
            if r.status_code in [201, 204]:
                return {'status': 'success'}
            return {'error': f"Failed to set secret: {r.text}"}

        except Exception as e: return {'error': str(e)}

    @staticmethod
    def delete_secret(owner, repo, name, account_id):
        token = GitHubManager._get_token_for_account(account_id)
        if not token: return {'error': 'Auth failed'}

        headers = {'Authorization': f'token {token}', 'Accept': 'application/vnd.github.v3+json'}
        try:
            url = f"https://api.github.com/repos/{owner}/{repo}/actions/secrets/{name}"
            r = requests.delete(url, headers=headers)
            if r.status_code == 204: return {'status': 'deleted'}
            return {'error': f"Failed to delete: {r.text}"}
        except Exception as e: return {'error': str(e)}

    @staticmethod
    def get_releases(repo_url, account_id=None):
        """
        Fetches list of releases for a given repo.
        Optionally uses an account token for higher rate limits.
        """
        try:
            # Clean repo string
            repo = repo_url.replace('https://github.com/', '').strip('/')

            headers = {'Accept': 'application/vnd.github.v3+json'}

            # Resolve Token
            token = None
            if account_id:
                token = GitHubManager._get_token_for_account(account_id)

            if token:
                headers['Authorization'] = f'token {token}'

            # Get List of Releases (First 30)
            url = f"https://api.github.com/repos/{repo}/releases?per_page=30"
            log(f"Fetching GitHub Releases: {url}")

            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code != 200:
                return {'error': f"GitHub API Error: {resp.status_code} {resp.reason}"}

            releases_data = resp.json()
            if not isinstance(releases_data, list):
                # Fallback if endpoint behaves unexpectedly or empty
                return []

            results = []
            for data in releases_data:
                release_info = {
                    'id': data.get('id'),
                    'tag': data.get('tag_name'),
                    'name': data.get('name'),
                    'published_at': data.get('published_at'),
                    'prerelease': data.get('prerelease', False),
                    'draft': data.get('draft', False),
                    'assets': []
                }

                for asset in data.get('assets', []):
                    release_info['assets'].append({
                        'id': asset['id'],
                        'name': asset['name'],
                        'size': asset['size'],
                        'download_url': asset['browser_download_url']
                    })

                results.append(release_info)

            return results

        except Exception as e:
            log(f"GitHub Error: {e}")
            return {'error': str(e)}

    @staticmethod
    def run_download_job(asset_url, filename, dest_path, account_id=None):
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

            headers = {}
            if account_id:
                token = GitHubManager._get_token_for_account(account_id)
                if token:
                    headers['Authorization'] = f'token {token}'
                    headers['Accept'] = 'application/octet-stream'
                    # Note: For public assets, browser_download_url is a redirect to S3
                    # and usually doesn't need auth, but API assets do.
                    # Requests handles redirects automatically.
                    # We only attach auth if it's NOT a raw S3 link (S3 rejects github auth headers).
                    # Actually, simple heuristic: try without auth first for assets?
                    # Most standard 'browser_download_url' are public S3.
                    # Providing header to S3 causes 400 Bad Request.
                    # We will strip header if redirected, but requests session logic is complex.
                    # SAFE BET: Don't use auth for public release asset downloads unless specifically private.
                    # For now, let's omit auth for downloads unless it fails.
                    # The user prompt implies context for "operations", but mostly publishing needs it.
                    pass # Trust requests to handle redirect auth stripping

            # Stream download
            with requests.get(asset_url, stream=True, headers=headers) as r:
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
                            if downloaded % (1024*1024) == 0: # Every 1MB
                                job_manager.update_job_details({'progress': f"{percent}%"})

            log(f"GitHub Download Complete: {filename}")
            NotificationManager.send_notification(f"✅ ParFix: Downloaded {filename} from GitHub")

        except Exception as e:
            log(f"Download Failed: {e}")
            job_manager.update_job_details({'error': str(e)})
            if os.path.exists(final_path):
                 try: os.remove(final_path)
                 except: pass

    @staticmethod
    def run_publish_job(repo, tag_name, file_path, account_id, body=None, prerelease=False, draft=False):
        """
        Background job to create a release and upload an asset.
        """
        repo = repo.replace('https://github.com/', '').strip('/')
        filename = os.path.basename(file_path)

        log(f"Starting GitHub Publish: {repo} @ {tag_name}")
        job_manager.update_job_details({'action': 'Creating Release...'})

        token = GitHubManager._get_token_for_account(account_id)
        if not token:
            job_manager.update_job_details({'error': 'Account token not found'})
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
                "body": body or "Uploaded via ParFix Utility",
                "draft": draft,
                "prerelease": prerelease
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
            upload_url_template = release_data['upload_url']
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

    @staticmethod
    def run_import_job(source_url, target_name, private, account_id):
        log(f"Starting Import: {source_url} -> {target_name}")
        token = GitHubManager._get_token_for_account(account_id)
        if not token:
            job_manager.update_job_details({'error': 'Account token not found'})
            return

        # Prepare URLs with Auth
        # Source Auth: Try to use the same token (assuming user owns it or has access)
        # If public, token doesn't hurt.
        clean_source = source_url.replace('https://', '').replace('http://', '')
        source_auth_url = f"https://oauth2:{token}@{clean_source}"

        temp_dir = f"/tmp/import_{target_name}_{os.getpid()}"

        try:
            # 1. Create Empty Repo
            log(f"Creating repository: {target_name}")
            job_manager.update_job_details({'action': 'Creating new repository...'})

            res = GitHubManager.create_repository(target_name, private, "Imported via ParFix", account_id)
            if 'error' in res:
                raise Exception(f"Failed to create repo: {res['error']}")

            new_repo_full = res['repo'] # owner/name
            new_repo_url = f"https://oauth2:{token}@github.com/{new_repo_full}.git"

            # 2. Clone Mirror
            log("Cloning source (Mirror)...")
            job_manager.update_job_details({'action': 'Cloning source repository...'})

            if os.path.exists(temp_dir): shutil.rmtree(temp_dir)
            os.makedirs(temp_dir)

            cmd_clone = ['git', 'clone', '--mirror', source_auth_url, '.']
            proc_clone = subprocess.Popen(
                cmd_clone, cwd=temp_dir, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True
            )
            job_manager.set_current_process(proc_clone)

            for line in proc_clone.stdout:
                if "Receiving objects" in line: log(f"[GIT CLONE] {line.strip()}")

            proc_clone.wait()
            if proc_clone.returncode != 0:
                raise Exception("Git Clone Failed. Check source URL or permissions.")

            # 3. Push Mirror
            if job_manager.is_cancelled(): return

            log("Pushing to new repository...")
            job_manager.update_job_details({'action': 'Pushing to new repository...'})

            cmd_push = ['git', 'push', '--mirror', new_repo_url]
            proc_push = subprocess.Popen(
                cmd_push, cwd=temp_dir, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True
            )
            job_manager.set_current_process(proc_push)

            for line in proc_push.stdout:
                log(f"[GIT PUSH] {line.strip()}")

            proc_push.wait()
            if proc_push.returncode != 0:
                raise Exception("Git Push Failed.")

            log("Import Successful")
            NotificationManager.send_notification(f"✅ ParFix: Imported {target_name} from {source_url}")

        except Exception as e:
            log(f"Import Failed: {e}")
            job_manager.update_job_details({'error': str(e)})
        finally:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)

    @staticmethod
    def delete_release(owner, repo, release_id, account_id):
        token = GitHubManager._get_token_for_account(account_id)
        if not token: return {'error': 'Auth failed'}

        headers = {'Authorization': f'token {token}', 'Accept': 'application/vnd.github.v3+json'}
        try:
            url = f"https://api.github.com/repos/{owner}/{repo}/releases/{release_id}"
            r = requests.delete(url, headers=headers)
            if r.status_code == 204: return {'status': 'deleted'}
            return {'error': f"Failed: {r.text}"}
        except Exception as e: return {'error': str(e)}

    @staticmethod
    def delete_release_asset(owner, repo, asset_id, account_id):
        token = GitHubManager._get_token_for_account(account_id)
        if not token: return {'error': 'Auth failed'}

        headers = {'Authorization': f'token {token}', 'Accept': 'application/vnd.github.v3+json'}
        try:
            url = f"https://api.github.com/repos/{owner}/{repo}/releases/assets/{asset_id}"
            r = requests.delete(url, headers=headers)
            if r.status_code == 204: return {'status': 'deleted'}
            return {'error': f"Failed: {r.text}"}
        except Exception as e: return {'error': str(e)}

    @staticmethod
    def get_repo_details(repo, account_id):
        token = GitHubManager._get_token_for_account(account_id)
        if not token: return {'error': 'Auth failed'}
        headers = {'Authorization': f'token {token}', 'Accept': 'application/vnd.github.v3+json'}

        try:
            r = requests.get(f"https://api.github.com/repos/{repo}", headers=headers)
            if r.status_code == 200:
                return r.json()
            return {'error': f"Failed to get details: {r.status_code}"}
        except Exception as e:
            return {'error': str(e)}

    @staticmethod
    def get_real_repo_size_bytes(repo, account_id):
        """
        Calculates the TRUE size of a repository by summing:
        1. Git Repo Size (Source)
        2. All Release Assets Size (Binary)
        Handles pagination for releases.
        """
        try:
            # 1. Get Git Size
            details = GitHubManager.get_repo_details(repo, account_id)
            if 'error' in details: return 0

            git_size_kb = details.get('size', 0)
            total_bytes = git_size_kb * 1024

            # 2. Get Release Assets Size
            token = GitHubManager._get_token_for_account(account_id)
            headers = {'Accept': 'application/vnd.github.v3+json'}
            if token: headers['Authorization'] = f'token {token}'

            page = 1
            while True:
                url = f"https://api.github.com/repos/{repo}/releases?per_page=100&page={page}"
                r = requests.get(url, headers=headers, timeout=10)
                if r.status_code != 200: break

                releases = r.json()
                if not releases or not isinstance(releases, list): break

                for rel in releases:
                    for asset in rel.get('assets', []):
                        total_bytes += asset.get('size', 0)

                if len(releases) < 100: break # Last page
                page += 1

            return total_bytes

        except Exception as e:
            log(f"Size Calc Error: {e}")
            return 0

    @staticmethod
    def find_available_pool_repo(account_id, base_name, limit_gb):
        """
        Scans for existing repositories matching base_name that have free space.
        Returns (full_repo_name, current_size_kb) or (None, 0).
        """
        try:
            repos = GitHubManager.list_user_repos(account_id)
            if isinstance(repos, dict) and 'error' in repos: return None, 0

            # Filter matching Base Name
            candidates = []
            for r in repos:
                r_name = r['name'].split('/')[-1]
                if r_name.startswith(base_name):
                    candidates.append(r['name'])

            # Sort by name (sequential)
            candidates.sort()

            limit_bytes = limit_gb * 1024 * 1024 * 1024

            for cand in candidates:
                # Use REAL size check
                current_bytes = GitHubManager.get_real_repo_size_bytes(cand, account_id)

                if current_bytes < limit_bytes:
                    current_kb = current_bytes / 1024
                    log(f"♻️ Pool: Found existing repo '{cand}' ({current_bytes/(1024*1024*1024):.2f}GB Used)")
                    return cand, current_kb

            return None, 0

        except Exception as e:
            log(f"Pool Scan Error: {e}")
            return None, 0

    @staticmethod
    def smart_publish_job(files, base_repo_name, tag, account_id, body=None, private=True, description="Archive Spanning", span_limit_gb=40, account_limit_gb=45, camouflage=False, meta=None, rate_limit_sleep=0, safety_sleep=0, strategy='relay', release_mode='create', strict_mode=False, distribution_map=None):
        """
        Publishes files across multiple repositories and accounts if needed.
        Strategies: 'relay' (Sequential Fill), 'scatter' (Round Robin per File).
        Release Mode: 'create' (New Tag) or 'append' (Add to latest).
        Strict Mode: If True, enforces 1 Repo per Account (Max 45GB) and switches account immediately if full.
        Distribution Map: List of dicts [{'account_id': '1', 'repo': 'user/repo'}] defining explicit routing.
        """
        from app.managers.obfuscation import ObfuscationManager
        from app.managers.survival_kit import SurvivalKitManager
        import time
        import random

        # Normalize Routing Logic
        # Case 1: Use distribution_map if provided (Professional Mode)
        # Case 2: Use account_ids list + base_repo_name (Legacy/Simple Mode)

        routing_mode = 'map' if distribution_map and len(distribution_map) > 0 else 'legacy'

        # Build unified accessors
        if routing_mode == 'map':
            account_ids = [str(item['account_id']) for item in distribution_map]
            # Helper to get repo for an account index
            def get_repo_target(idx):
                if idx < len(distribution_map):
                    return distribution_map[idx]['repo']
                return base_repo_name # Fallback
        else:
            # Legacy logic normalization
            account_ids = []
            if isinstance(account_id, list):
                account_ids = account_id
            elif isinstance(account_id, str) and ',' in account_id:
                account_ids = [aid.strip() for aid in account_id.split(',') if aid.strip()]
            else:
                account_ids = [str(account_id)]

            def get_repo_target(idx):
                return base_repo_name

        current_acc_idx = 0
        current_acc_id = account_ids[0]
        # Initial Repo Name Selection
        current_repo_name = get_repo_target(current_acc_idx)
        # If strict mode, we use full name. If not strict, we might append -01
        # But 'ensure_repo' logic below handles suffixing for non-strict.
        # Wait, ensure_repo takes 'name'. Ideally distribution_map provides FULL name 'user/repo'.
        # We need to adapt ensure_repo logic.

        # Build Username Map for Smart Identity
        accounts_list = GitHubManager.list_accounts()
        id_to_user = {str(a['id']): a['username'] for a in accounts_list}

        log(f"Starting Smart Publish: {len(files)} files -> {base_repo_name}* (Accounts: {len(account_ids)})")

        restore_map = {}
        active_files = files

        # 1. Camouflage Logic (Adaptive)
        # We now handle camouflage per-file inside the loop to support adaptive contexts.
        release_tag = tag
        release_title = f"Archive {tag}"
        release_body = body

        # Context Cache: repo_full -> {template, tag, title, body}
        repo_context_cache = {}

        if camouflage:
            log("🛡️ Adaptive Camouflage Mode: ON")

        # 2. Repo Spanning Logic
        current_repo_index = 1

        # If routing_mode is map, current_repo_name IS the target (no suffix).
        # If legacy, we suffix '-01' unless strict mode or single repo.

        if routing_mode == 'map':
             # Use explicit name from map.
             # If strict mode is OFF, do we still suffix?
             # Professional mode usually implies explicit control.
             # Let's assume Map = Exact Name unless strict mode is OFF and it fills up?
             # For strict mode, Map = Exact Name.
             # For non-strict, we can stick to Exact Name first, then suffix if needed.
             pass
        else:
             if not strict_mode:
                 current_repo_name = f"{base_repo_name}-{current_repo_index:02d}"
             else:
                 current_repo_name = base_repo_name

        # Helper to get/create repo (Bound to current account)
        def ensure_repo(name, acc_id, try_pool=False):
            # --- Dynamic Pooling Logic ---
            # Only relevant for 'legacy' naming. If 'map' is used, user specified exact target.
            if try_pool and routing_mode == 'legacy':
                pool_repo, pool_size = GitHubManager.find_available_pool_repo(acc_id, name, span_limit_gb)
                if pool_repo:
                    return pool_repo, pool_size

            # Check existence (Standard)
            user_info = GitHubManager._fetch_user_profile(GitHubManager._get_token_for_account(acc_id))
            owner = user_info['username']

            # Handle Name Normalization (Strip owner if present in map)
            if '/' in name:
                supplied_owner, short_name = name.split('/', 1)
                if supplied_owner.lower() == owner.lower():
                    name = short_name

            full_name = f"{owner}/{name}"

            # Check TRUE size (including releases)
            # This is critical for Strict Mode to work correctly.
            real_bytes = GitHubManager.get_real_repo_size_bytes(full_name, acc_id)
            return full_name, real_bytes / 1024 # Convert to KB for compatibility

            # --- Stealth Import Logic ---
            use_stealth = False
            if meta and meta.get('use_stealth_import'):
                use_stealth = True

            if use_stealth:
                conf = config.load_config()
                templates = conf.get('stealth_templates', [])
                if templates:
                    # Pick Random Template
                    source_url = random.choice(templates).strip()
                    if source_url:
                        log(f"🕵️ Stealth Mode: Importing {source_url} -> {name}")
                        GitHubManager.run_import_job(source_url, name, private, acc_id)
                        # After import, return repo name and size (assume small init size)
                        # We return name because run_import_job doesn't return the full name object directly, but it creates owner/name
                        return full_name, 1000 # 1MB dummy size for the clone

            # Standard Create if missing or no stealth
            log(f"Creating repository: {name} on account {acc_id}")
            res = GitHubManager.create_repository(name, private, description, acc_id)
            if 'error' in res:
                raise Exception(f"Failed to create repo {name}: {res['error']}")

            return res['repo'], 0

        # Upload Loop
        uploaded_assets = []

        # Cache for Scatter mode (repo_name -> upload_url) per account
        # Structure: { acc_id: { repo_name: upload_url } }
        scatter_cache = {}

        # Spanning Tracking
        spanning_map = {} # Key: "acc_id|repo_full", Value: { info_dict }

        def track_spanning(acc_id, r_full, r_url, f_size):
            key = f"{acc_id}|{r_full}"
            if key not in spanning_map:
                username = id_to_user.get(str(acc_id), 'Unknown')
                spanning_map[key] = {
                    'repo_name': r_full.split('/')[-1], # Short Name
                    'account': username,
                    'account_id': str(acc_id),
                    'url': r_url,
                    'file_count': 0,
                    'size_bytes': 0
                }
            spanning_map[key]['file_count'] += 1
            spanning_map[key]['size_bytes'] += f_size

        try:
            # Determine Allocation Mode
            allocation_mode = 'new'
            if meta and meta.get('allocation_mode') == 'fill':
                allocation_mode = 'fill'
                log("♻️ Allocation Mode: Fill Existing (Dynamic Pooling)")

            # IMPORTANT: In Strict Mode, we treat 'fill' as default if not specified?
            # Or assume we want to fill the target repo.
            # But the key is that current_size_gb MUST be accurate from start.

            # Init state for Relay
            use_pool = (allocation_mode == 'fill')

            # Determine initial target based on strategy
            initial_target_name = current_repo_name
            if use_pool and routing_mode == 'legacy':
                 initial_target_name = base_repo_name # Pool scans base

            repo_full, repo_size_kb = ensure_repo(initial_target_name, current_acc_id, try_pool=use_pool)

            # Update loop state
            current_size_gb = repo_size_kb / (1024 * 1024)
            current_acc_uploaded_gb = 0

            # Helper to create release return (upload_url, html_url)
            def get_release_data(r_name, t_name, acc_id):
                token = GitHubManager._get_token_for_account(acc_id)
                headers = {'Authorization': f'token {token}', 'Accept': 'application/vnd.github.v3+json'}
                create_url = f"https://api.github.com/repos/{r_name}/releases"
                payload = {
                    "tag_name": t_name,
                    "name": release_title,
                    "body": release_body,
                    "draft": False,
                    "prerelease": False
                }

                get_url = f"https://api.github.com/repos/{r_name}/releases/tags/{t_name}"
                gr = requests.get(get_url, headers=headers)
                if gr.status_code == 200:
                    d = gr.json()
                    return d['upload_url'], d['html_url']

                pr = requests.post(create_url, json=payload, headers=headers)
                if pr.status_code in [200, 201]:
                    d = pr.json()
                    return d['upload_url'], d['html_url']
                raise Exception(f"Failed to create release on {r_name}")

            # Initial Release (First Repo)
            # We delay release creation until inside the loop for Adaptive Camouflage

            final_release_url = None # Keep track of primary link
            current_release_url = None

            total_files = len(active_files)

            for idx, file_path in enumerate(active_files):
                if job_manager.is_cancelled(): break

                file_size_bytes = os.path.getsize(file_path)
                file_size_gb = file_size_bytes / (1024 * 1024 * 1024)

                # Check for Account Switch Requirement (Strict Mode Immediate Check)
                # If Strict Mode is on, we check if the CURRENT repo + NEW file > 45GB.
                # If so, we MUST switch account before even trying to upload.

                strict_limit_kb = 45 * 1024 * 1024 # 45GB in KB
                current_kb = current_size_gb * 1024 * 1024
                file_kb = file_size_bytes / 1024

                # We do this logic inside the loop, but BEFORE Scatter/Relay branch?
                # Actually Scatter branch handles its own selection.
                # Relay branch handles limit checks.
                # But Strict Mode is a global override essentially.

                # Let's rely on the Relay branch logic below, but verify 'current_size_gb' is fresh.

                # --- STRATEGY: SCATTER (Round Robin) ---
                if strategy == 'scatter' and len(account_ids) > 1:
                    # Determine Account
                    current_acc_idx = idx % len(account_ids)
                    current_acc_id = account_ids[current_acc_idx]

                    tgt_repo = current_repo_name # e.g. archive-01

                    # Check cache for REPO existence (not context yet)
                    if current_acc_id not in scatter_cache: scatter_cache[current_acc_id] = {}

                    if tgt_repo not in scatter_cache[current_acc_id]:
                        # Init repo on this account
                        use_pool = (allocation_mode == 'fill')
                        r_full, r_size = ensure_repo(base_repo_name if use_pool else tgt_repo, current_acc_id, try_pool=use_pool)
                        # We don't create release here anymore, just cache the repo info
                        scatter_cache[current_acc_id][tgt_repo] = {'repo': r_full, 'size': r_size}

                    repo_full = scatter_cache[current_acc_id][tgt_repo]['repo']
                    # Repo Size tracking is harder in scatter mode without re-querying,
                    # but we only use it for limits which scatter ignores (Round Robin implies infinite/balanced).
                    # Actually scatter limits are per-account.

                # --- STRATEGY: RELAY (Sequential) ---
                else:
                    # Check Repo Limit OR Account Switch Requirement
                    # Strict Mode: Hard 45GB limit on Repo (which equals Account limit)
                    effective_repo_limit = 45 if strict_mode else span_limit_gb
                    effective_acc_limit = 45 if strict_mode else account_limit_gb

                    repo_limit_reached = (current_size_gb + file_size_gb > effective_repo_limit)
                    account_limit_reached = (current_acc_uploaded_gb + file_size_gb > effective_acc_limit)

                    # Strict Mode Override:
                    # If Repo Limit is reached in Strict Mode, it implies Account Limit is also reached
                    # because we enforced 1 Repo = 1 Account.
                    if strict_mode and repo_limit_reached:
                        account_limit_reached = True

                    if repo_limit_reached or account_limit_reached:
                        # Switch Account Logic
                        # If strict mode, even repo_limit triggers account switch
                        should_switch_account = account_limit_reached or (strict_mode and repo_limit_reached)

                        if should_switch_account:
                            if len(account_ids) > 1:
                                log(f"Account {current_acc_id} limit reached ({current_acc_uploaded_gb:.2f}GB / Repo {current_size_gb:.2f}GB). Switching...")
                                if safety_sleep > 0:
                                    log(f"💤 Safety Sleep for {safety_sleep}s...")
                                    job_manager.update_job_details({'action': f"Cooling down ({safety_sleep}s)..."})
                                    time.sleep(safety_sleep)

                                current_acc_idx = (current_acc_idx + 1) % len(account_ids)
                                current_acc_id = account_ids[current_acc_idx]
                                current_acc_uploaded_gb = 0

                                # Reset Repo Index for new account?
                                # Strict Mode: Use base name again (try 'repo', then 'repo-02' if 'repo' full?
                                # No, strictly 1 repo means we check THE repo.)
                                # If strict mode, we should check 'base_repo_name' on new account.
                                # Strict Mode / Map Logic: Update Repo Name for new account
                                if strict_mode or routing_mode == 'map':
                                    # Get the specific repo for this new account index
                                    current_repo_name = get_repo_target(current_acc_idx)

                                    # Ensure we get the actual size
                                    repo_full, repo_size_kb = ensure_repo(current_repo_name, current_acc_id, try_pool=False)
                                    current_size_gb = repo_size_kb / (1024 * 1024)
                                    # Reset uploaded count
                                    current_acc_uploaded_gb = 0

                                    # Update context cache for new repo
                                    # We need to force a context refresh because 'repo_full' changed!
                                    # Clear previous context from cache to force regeneration in loop logic
                                    if repo_full in repo_context_cache:
                                        del repo_context_cache[repo_full]

                                    # Force RE-INIT logic below to run by ensuring it's not in cache or manually setting it
                                    # Ideally we should let the 'if repo_full not in repo_context_cache:' block handle it.
                                    # But we are inside the loop. The variable 'upload_url_template' needs to be updated for THIS file.

                                    # We can't rely on the loop flow falling through because we are in the 'else' (Relay) block.
                                    # The 'Adaptive Context' block comes AFTER this.
                                    # So if we reset 'repo_context_cache', the next block 'ensure_release_context' (or equivalent) will run.
                                    # Wait, the code structure is:
                                    # Loop -> Strategy (Relay/Scatter) -> Context Logic -> Upload.

                                    # Correct! So we just need to update 'repo_full' and 'current_acc_id' here.
                                    # The context block below uses 'repo_full' and 'current_acc_id'.
                                    # So we DON'T need to manually call get_release_data here IF we clear the cache/ensure logic runs.

                                    # Let's rely on the downstream block.

                                    # Force context cache update for next iteration logic
                                    if repo_full in repo_context_cache:
                                        del repo_context_cache[repo_full]

                                log(f"Switched to Account: {current_acc_id} -> {current_repo_name}")
                            else:
                                log("⚠️ Limit reached but no more accounts available!")
                                # If strict mode, we might just stop or error?
                                # Proceeding will overfill.
                                pass

                        # Switch Repo Logic (Within same account)
                        # Only if NOT Strict Mode OR if Account Switch didn't happen (e.g. single account config)
                        # The 'elif' ensures we don't double-switch if we just switched accounts.
                        # BUT: If strict mode is on, we NEVER want to switch repos locally.
                        # So 'elif not strict_mode' handles that.
                        elif not strict_mode:
                            log(f"Switching Repository...")

                            can_reuse = False
                            if allocation_mode == 'fill':
                                 # Try to find another bucket
                                 pool_repo, pool_size = GitHubManager.find_available_pool_repo(current_acc_id, base_repo_name, span_limit_gb)
                                 if pool_repo and pool_repo != repo_full:
                                     repo_full = pool_repo
                                     repo_size_kb = pool_size
                                     can_reuse = True

                            if not can_reuse:
                                current_repo_index += 1
                                current_repo_name = f"{base_repo_name}-{current_repo_index:02d}"
                                repo_full, _ = ensure_repo(current_repo_name, current_acc_id)
                                repo_size_kb = 0

                            current_size_gb = repo_size_kb / (1024 * 1024)

                # --- ADAPTIVE CAMOUFLAGE & CONTEXT ---

                # Helper to update Release Data based on context
                def ensure_release_context(r_full, acc_id):
                    if r_full in repo_context_cache:
                        return repo_context_cache[r_full]

                    # Detect Context
                    detected_template = None
                    # If using Fill mode, we might have history
                    if allocation_mode == 'fill':
                        releases = GitHubManager.get_releases(r_full, acc_id)
                        if releases and isinstance(releases, list) and len(releases) > 0:
                            # Heuristic: Check latest release title
                            latest = releases[0]
                            detected_template = ObfuscationManager.detect_template(latest.get('name', ''))
                            if detected_template:
                                log(f"🕵️ Detected existing theme for {r_full}: {detected_template}")

                    # Fallback or New
                    if not detected_template:
                        # User preference or Random
                        base_pref = meta.get('camo_template', 'random') if meta else 'random'
                        # If base_pref is fixed (e.g. 'log_rotation'), we use it.
                        detected_template = base_pref

                    # Generate Metadata
                    boring = ObfuscationManager.generate_boring_metadata(detected_template)

                    # --- SMART APPEND LOGIC ---
                    target_tag = boring['tag']
                    target_title = boring['title']
                    target_body = boring['body']
                    is_append = False

                    if release_mode == 'append':
                        # Try to find LATEST release to append to
                        releases = GitHubManager.get_releases(r_full, acc_id)
                        if releases and len(releases) > 0:
                            latest = releases[0]
                            log(f"📎 Smart Append: Found existing release '{latest['tag']}' on {r_full}")
                            target_tag = latest['tag']
                            target_title = latest['name']
                            is_append = True

                            # Update Template Context from Latest Release
                            # This is crucial so ObfuscationManager knows which pattern to use (e.g. ai_weights vs log_rotation)
                            detected_template_from_release = ObfuscationManager.detect_template(latest.get('name', ''))
                            if detected_template_from_release:
                                detected_template = detected_template_from_release # Update detected for boring gen if we re-gen
                                boring['template'] = detected_template_from_release # Force update boring
                                log(f"📎 Smart Append: Adopted template '{detected_template}' from existing release.")

                            # We keep the detected template (from context) or boring template
                        else:
                            log(f"⚠️ Smart Append: No release found on {r_full}, falling back to CREATE.")

                    # Create/Get Release
                    # We use the generated tag/title/body
                    u_url, r_url = get_release_data(r_full, target_tag, acc_id)

                    # Ensure ctx gets the potentially updated template from 'Smart Append' block
                    ctx = {
                        'template': boring['template'],
                        'upload_url': u_url,
                        'html_url': r_url,
                        'tag': target_tag,
                        'is_append': is_append
                    }
                    repo_context_cache[r_full] = ctx
                    log(f"🎭 Context for {r_full}: {boring['title']} ({boring['template']})")
                    return ctx

                # Redefine get_release_data inside loop to use specific metadata?
                # No, let's just copy the logic or update the helper.
                # The helper 'get_release_data' above (in previous block) used 'release_title' (global to func).
                # We need to make it dynamic.
                # Let's override the logic here:

                # The loop relies on repo_context_cache[repo_full].
                # If it's NOT in cache, we need to initialize it.
                # BUT wait, the block above ('if repo_full not in repo_context_cache:') is structured wrong.
                # It seems I have duplicate logic or misplaced blocks.
                # The big block above (ensure_release_context replacement) handles INIT.
                # Let's verify if the logic flows correctly.

                # Logic Flow:
                # 1. Check if repo_full in cache.
                # 2. If NOT, init context (detect template, check append mode, create/get release).
                # 3. Use context.

                if repo_full not in repo_context_cache:
                    # Resolve Template
                    base_pref = meta.get('camo_template', 'random') if meta else 'random'

                    # Detect existing for FILL mode
                    if allocation_mode == 'fill':
                         rels = GitHubManager.get_releases(repo_full, current_acc_id)
                         if rels and len(rels) > 0:
                             det = ObfuscationManager.detect_template(rels[0].get('name', ''))
                             if det: base_pref = det

                    boring = ObfuscationManager.generate_boring_metadata(base_pref)

                    # --- SMART APPEND LOGIC (Duplicate for Loop safety) ---
                    target_tag = boring['tag']
                    target_title = boring['title']
                    is_append = False

                    if release_mode == 'append':
                        releases = GitHubManager.get_releases(repo_full, current_acc_id)
                        if releases and len(releases) > 0:
                            latest = releases[0]
                            target_tag = latest['tag']
                            target_title = latest['name']
                            is_append = True

                            det = ObfuscationManager.detect_template(latest.get('name', ''))
                            if det:
                                boring['template'] = det
                                log(f"📎 Smart Append: Adopted template '{det}'")

                    # Create Release
                    token = GitHubManager._get_token_for_account(current_acc_id)
                    headers = {'Authorization': f'token {token}', 'Accept': 'application/vnd.github.v3+json'}

                    # If Appending, we skip POST and go straight to GET usually,
                    # unless it's missing (fallback handled by get_release_data equivalent logic below).

                    # Check if tag exists (Collision check)
                    # Use target_tag (which might be boring['tag'] or existing tag)

                    create_url = f"https://api.github.com/repos/{repo_full}/releases"
                    payload = {
                        "tag_name": target_tag,
                        "name": target_title,
                        "body": boring['body'],
                        "draft": False,
                        "prerelease": False
                    }

                    # Try Create (Only if not append mode, OR if we want to try anyway)
                    # Ideally if is_append, we shouldn't create.

                    if is_append:
                        # Skip create attempt, force get
                        r = requests.Response()
                        r.status_code = 422 # Already exists simulation
                    else:
                        r = requests.post(create_url, json=payload, headers=headers)
                    if r.status_code in [200, 201]:
                        d = r.json()
                        u_url = d['upload_url']
                        h_url = d['html_url']
                    else:
                        # Fallback: Get existing (if we guessed tag correctly or collision)
                        # Or if we want to APPEND to existing release?
                        # Spanning usually means unique releases.
                        # If failed, maybe try GET
                        get_url = f"https://api.github.com/repos/{repo_full}/releases/tags/{target_tag}"
                        gr = requests.get(get_url, headers=headers)
                        if gr.status_code == 200:
                            d = gr.json()
                            u_url = d['upload_url']
                            h_url = d['html_url']
                        else:
                            raise Exception(f"Failed to create/find release {target_tag} on {repo_full}: {r.text}")

                    repo_context_cache[repo_full] = {
                        'template': boring['template'],
                        'upload_url': u_url,
                        'html_url': h_url,
                        'tag': target_tag,
                        'is_append': is_append
                    }
                    log(f"🎭 Context for {repo_full}: {target_title} ({boring['template']})")

                ctx = repo_context_cache[repo_full]
                upload_url_template = ctx['upload_url']
                current_release_url = ctx['html_url']
                current_template_name = ctx['template']

                if not final_release_url: final_release_url = current_release_url

                # Rename File (Just-In-Time)
                original_name = os.path.basename(file_path)
                final_path_to_upload = file_path
                clean_up_needed = False

                if camouflage:
                    # Smart Sequence Naming if Appending
                    if ctx.get('is_append', False):
                        # Fetch existing assets to determine next sequence
                        # We need to query the release assets.
                        # Optimization: We can't query API for every file.
                        # But we are in a loop. We should cache the 'existing_assets' list in context.
                        if 'assets' not in ctx:
                             # Fetch assets
                             rels = GitHubManager.get_releases(repo_full, current_acc_id)
                             # Find the matching tag
                             ctx['assets'] = []
                             for r in rels:
                                 if r['tag'] == ctx['tag']:
                                     ctx['assets'] = [a['name'] for a in r['assets']]
                                     break

                        fake_name = ObfuscationManager.get_next_sequence_name(ctx['assets'], original_name, current_template_name)
                        # Add this new name to local cache so next file increments properly
                        ctx['assets'].append(fake_name)
                    else:
                        fake_name = ObfuscationManager.get_camouflaged_filename(original_name, current_template_name)

                    # We need to copy/rename to a temp location to avoid modifying the original list if reused?
                    # But files are consumed.
                    # Using same dir
                    fake_path = os.path.join(os.path.dirname(file_path), fake_name)
                    try:
                        os.rename(file_path, fake_path)
                        final_path_to_upload = fake_path
                        restore_map[fake_name] = original_name
                        clean_up_needed = True
                    except Exception as e:
                        log(f"Renaming failed: {e}")
                        # Fallback to original
                        final_path_to_upload = file_path

                # Upload
                fname = os.path.basename(final_path_to_upload)
                job_manager.update_job_details({'action': f"Uploading {idx+1}/{total_files}: {fname} to {current_repo_name} ({current_acc_id})"})

                token = GitHubManager._get_token_for_account(current_acc_id)
                headers = {'Authorization': f'token {token}', 'Content-Type': 'application/octet-stream'}

                real_upload_url = upload_url_template.split('{')[0] + f"?name={fname}"

                upload_success = False
                try:
                    with open(final_path_to_upload, 'rb') as f:
                        r = requests.post(real_upload_url, data=f, headers=headers)
                        if r.status_code in [200, 201]:
                            upload_success = True
                            adata = r.json()
                            uploaded_assets.append({
                                'name': fname,
                                'size': file_size_bytes,
                                'url': adata.get('browser_download_url', ''),
                                'repo': repo_full,
                                'account_id': str(current_acc_id),
                                'username': id_to_user.get(str(current_acc_id), 'Unknown')
                            })
                            current_size_gb += file_size_gb
                            current_acc_uploaded_gb += file_size_gb
                            # Success - Track Metadata
                            track_spanning(current_acc_id, repo_full, current_release_url, file_size_bytes)
                        else:
                            log(f"Failed upload {fname}: {r.text}")
                finally:
                    # Rename back to original name if we camouflaged it
                    if clean_up_needed and final_path_to_upload != file_path:
                        try:
                            os.rename(final_path_to_upload, file_path)
                            # log(f"Restored original filename: {original_name}")
                        except Exception as e:
                            log(f"Failed to restore filename {original_name}: {e}")

                if not upload_success:
                    continue

                # Rate Limit Sleep
                if rate_limit_sleep > 0:
                    time.sleep(rate_limit_sleep)

            # Save Map Logic
            if camouflage and restore_map:
                 ObfuscationManager.save_map_file(restore_map, base_repo_name)

            log(f"Smart Publish Complete. {len(uploaded_assets)} assets across repos.")

            # Convert map to list for storage
            # Add human size string
            spanning_info = list(spanning_map.values())
            for item in spanning_info:
                # Simple human size
                s = item['size_bytes']
                item['size_human'] = f"{s:.2f} B" # Default
                for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
                    if s < 1024:
                        item['size_human'] = f"{s:.2f} {unit}"
                        break
                    s /= 1024
                else:
                    item['size_human'] = f"{s:.2f} PB"

            # --- SURVIVAL KIT GENERATION ---
            # We generate it in the source folder of the first file
            if active_files and camouflage:
                try:
                    source_dir = os.path.dirname(active_files[0])
                    SurvivalKitManager.generate_kit(source_dir, release_title, restore_map, spanning_info)
                except Exception as ek:
                    log(f"⚠️ Survival Kit generation error: {ek}")

            # Return data structure for Catalog
            for item in spanning_info:
                # Simple human size
                s = item['size_bytes']
                item['size_human'] = f"{s:.2f} B" # Default
                for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
                    if s < 1024:
                        item['size_human'] = f"{s:.2f} {unit}"
                        break
                    s /= 1024
                else:
                    # If loop finishes (larger than TB)
                    item['size_human'] = f"{s:.2f} PB"

            # Return data structure for Catalog
            return {
                'assets': uploaded_assets,
                'restore_map': restore_map,
                'repo_base': base_repo_name,
                'release_url': final_release_url,
                'spanning_info': spanning_info
            }

        except Exception as e:
            log(f"Smart Publish Failed: {e}")
            raise e

    @staticmethod
    def run_batch_download_job(assets, dest_root, account_id):
        """
        Downloads multiple assets in parallel.
        assets: list of dicts {'url': ..., 'filename': ...}
        """
        import concurrent.futures

        total = len(assets)
        log(f"Starting Batch Download: {total} files")
        job_manager.update_job_details({'action': f'Starting Batch Download ({total} files)'})

        if not os.path.exists(dest_root):
            os.makedirs(dest_root, exist_ok=True)

        # Default Token (Fallback)
        default_token = GitHubManager._get_token_for_account(account_id)
        default_headers = {}
        if default_token:
            default_headers['Authorization'] = f'token {default_token}'
            default_headers['Accept'] = 'application/octet-stream'

        # Smart Identity: Pre-fetch tokens AND current usernames for all involved accounts
        identity_tokens = {}
        identity_usernames = {}

        # Load all accounts config once to map IDs to current Usernames
        all_accounts = GitHubManager.list_accounts()
        id_to_current_user = {str(a['id']): a['username'] for a in all_accounts}

        for asset in assets:
            aid = asset.get('account_id')
            if aid:
                aid_str = str(aid)
                if aid_str not in identity_tokens:
                    t = GitHubManager._get_token_for_account(aid)
                    if t:
                        identity_tokens[aid_str] = t
                        # Store current username for self-healing
                        if aid_str in id_to_current_user:
                            identity_usernames[aid_str] = id_to_current_user[aid_str]

        completed = 0
        errors = 0

        # Regex for patching URL
        import re
        url_pattern = re.compile(r'^(https?://github\.com/)([^/]+)(/.*)$')

        def download_one(asset):
            url = asset['url']
            # Support both 'filename' (API) and 'name' (Catalog) keys
            name = asset.get('filename') or asset.get('name')
            if not name: return False

            path = os.path.join(dest_root, name)

            # Determine Headers (Smart Switch)
            use_headers = default_headers.copy()
            aid = asset.get('account_id')

            if aid:
                aid_str = str(aid)
                if aid_str in identity_tokens:
                    use_headers['Authorization'] = f"token {identity_tokens[aid_str]}"
                    use_headers['Accept'] = 'application/octet-stream'

                    # --- Self-Healing Logic ---
                    # If we have a current username map, check if URL matches it
                    if aid_str in identity_usernames:
                        current_user = identity_usernames[aid_str]
                        match = url_pattern.match(url)
                        if match:
                            base, old_user, rest = match.groups()
                            if old_user != current_user:
                                # Patch the URL
                                new_url = f"{base}{current_user}{rest}"
                                log(f"🔧 Self-Healing URL: {old_user} -> {current_user}")
                                url = new_url

            try:
                # Basic download without progress tracking per file to simplify batch logic
                # We trust requests.get handling redirects
                with requests.get(url, headers=use_headers, stream=True) as r:
                    r.raise_for_status()
                    with open(path, 'wb') as f:
                        for chunk in r.iter_content(chunk_size=8192):
                            if job_manager.is_cancelled(): return False
                            f.write(chunk)
                return True
            except Exception as e:
                log(f"Error downloading {name}: {e}")
                return False

        # Use ThreadPoolExecutor
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            # Map futures to assets
            future_to_asset = {executor.submit(download_one, asset): asset for asset in assets}

            for future in concurrent.futures.as_completed(future_to_asset):
                if job_manager.is_cancelled():
                    log("Batch Download Cancelled")
                    executor.shutdown(wait=False, cancel_futures=True)
                    return

                res = future.result()
                if res:
                    completed += 1
                else:
                    errors += 1

                percent = int((completed + errors) / total * 100)
                job_manager.update_job_details({
                    'progress': f"{percent}%",
                    'action': f"Downloaded {completed}/{total} (Errors: {errors})"
                })

        log(f"Batch Download Finished. Success: {completed}, Errors: {errors}")
        NotificationManager.send_notification(f"✅ ParFix: Batch Downloaded {completed} files")
        return {'success': completed, 'errors': errors}
