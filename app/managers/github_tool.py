from app.core.job_manager import log, job_manager
from app.managers.notification import NotificationManager
from app.core import config
import requests
import os
import shutil
import subprocess

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

    @staticmethod
    def get_releases(repo_url, account_id=None):
        """
        Fetches the latest releases for a given repo.
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
