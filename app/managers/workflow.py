import json
import os
import uuid
import logging
import time
import threading
import base64
import shutil
from datetime import datetime
from app.managers.sync import SyncManager
from app.core.job_manager import job_manager, log

# Import Managers for execution
from app.managers.archive import ArchiveManager
from app.managers.github_tool import GitHubManager
from app.managers.catalog import CatalogManager

logger = logging.getLogger(__name__)

class WorkflowManager:
    """
    Manages and Executes Automation Workflows.
    """
    def __init__(self):
        # Paths
        self.primary_dir = SyncManager.DATA_DIR
        self.fallback_dir = "."
        self.filename = "workflows.json"
        self.path = self._resolve_path(self.filename)

        self.workflows = self.load_workflows()

    def _resolve_path(self, filename):
        if SyncManager.is_configured():
            return os.path.join(self.primary_dir, filename)
        return os.path.join(self.fallback_dir, filename)

    def load_workflows(self):
        if not os.path.exists(self.path):
            return []
        try:
            with open(self.path, 'r') as f:
                return json.load(f)
        except: return []

    def save_workflows(self):
        try:
            with open(self.path, 'w') as f:
                json.dump(self.workflows, f, indent=2)
            if SyncManager.is_configured():
                SyncManager.push_data("Updated workflows.json")
            return True
        except: return False

    def get_all(self):
        return self.workflows

    def create_workflow(self, name, steps):
        wf = {
            "id": str(uuid.uuid4()),
            "name": name,
            "steps": steps, # List of {type, config}
            "created_at": datetime.now().isoformat()
        }
        self.workflows.append(wf)
        self.save_workflows()
        return wf

    def delete_workflow(self, wf_id):
        self.workflows = [w for w in self.workflows if w['id'] != wf_id]
        self.save_workflows()
        return True

    # --- Execution Engine ---

    @staticmethod
    def execute_workflow_job(wf_id, input_paths, wf_data):
        """
        The Master Job that runs steps sequentially.
        input_paths: List of files selected in UI.
        wf_data: The full workflow object.
        """
        log(f"🚀 Starting Workflow: {wf_data['name']}")

        context = {
            'files': input_paths, # Current active files
            'initial_files': input_paths,
            'github_assets': [], # To collect upload URLs
            'catalog_entry': None,
            'meta': {} # For pre-indexing data
        }

        try:
            for i, step in enumerate(wf_data['steps']):
                step_type = step['type']
                conf = step['config']
                log(f"▶️ Step {i+1}/{len(wf_data['steps'])}: {step_type}")
                job_manager.update_job_details({'action': f"Step {i+1}: {step_type}"})

                if step_type == 'analyze_source':
                    context['meta'] = WorkflowManager._step_analyze(context['files'])
                elif step_type == 'pack':
                    context['files'] = WorkflowManager._step_pack(context['files'], conf)
                elif step_type == 'github_publish':
                    context['github_assets'] = WorkflowManager._step_gh_publish(context['files'], conf, context['meta'])
                elif step_type == 'catalog_add':
                    WorkflowManager._step_catalog(context, conf)

                time.sleep(1) # Small breathe

            log(f"✅ Workflow '{wf_data['name']}' Completed Successfully!")
            job_manager.update_job_details({'action': 'Completed', 'progress': '100%'})

        except Exception as e:
            log(f"❌ Workflow Failed at Step {i+1}: {e}")
            job_manager.update_job_details({'error': str(e)})
            raise e

    # --- Step Implementations ---

    @staticmethod
    def _step_analyze(files):
        """
        Scans source folder for Pre-Indexing metadata (Tree, Size, Count).
        Enforces 'Folder First' condition.
        Scans Root for Cover Images.
        """
        if not files: raise Exception("No input files for Analysis")

        # Enforce Folder
        target_path = files[0]
        if not os.path.isdir(target_path):
            log(f"⚠️ Input '{os.path.basename(target_path)}' is a file. Creating wrapper folder...")
            # Auto-wrap file in folder
            folder_name = os.path.splitext(os.path.basename(target_path))[0]
            parent = os.path.dirname(target_path)
            new_folder = os.path.join(parent, folder_name)

            if not os.path.exists(new_folder):
                os.makedirs(new_folder)

            new_file_path = os.path.join(new_folder, os.path.basename(target_path))
            shutil.move(target_path, new_file_path)
            target_path = new_folder
            log(f"✅ Wrapped in: {new_folder}")

        # Build Tree & Stats
        tree_lines = []
        total_size = 0
        file_count = 0
        dir_count = 0
        cover_image = None

        # Scan Root for Cover Image (jpg, png, webp, jpeg)
        # Only in ROOT of target_path, not subfolders.
        for f in os.listdir(target_path):
            fp = os.path.join(target_path, f)
            if os.path.isfile(fp):
                ext = os.path.splitext(f)[1].lower()
                if ext in ['.jpg', '.jpeg', '.png', '.webp']:
                    if not cover_image: # Take first found
                        cover_image = fp
                        log(f"📸 Found Cover Image: {f}")

        for root, dirs, filenames in os.walk(target_path):
            level = root.replace(target_path, '').count(os.sep)
            indent = ' ' * 4 * (level)
            tree_lines.append(f"{indent}{os.path.basename(root)}/")
            dir_count += 1
            for f in filenames:
                fp = os.path.join(root, f)
                size = os.path.getsize(fp)
                total_size += size
                file_count += 1
                tree_lines.append(f"{indent}    {f} ({WorkflowManager._human_size(size)})")

        tree_text = "\n".join(tree_lines)

        log(f"Analysis Complete: {file_count} files, {WorkflowManager._human_size(total_size)}")

        return {
            'title': os.path.basename(target_path),
            'tree_text': tree_text,
            'total_size': total_size,
            'file_count': file_count,
            'folder_path': target_path,
            'cover_image': cover_image,
            'missing_cover': (cover_image is None)
        }

    @staticmethod
    def _step_pack(files, conf):
        """
        Runs Packer. Returns list of generated RAR/PAR2 files.
        """
        target_path = files[0]
        original_name = os.path.basename(target_path)
        name = original_name

        # Obfuscation Logic
        obfuscate = conf.get('obfuscate', False)
        if obfuscate:
            # Base64 Encode Filename (URL Safe)
            name_b64 = base64.urlsafe_b64encode(original_name.encode('utf-8')).decode('utf-8')
            name = name_b64.rstrip('=') # Remove padding for cleaner filenames
            log(f"🕵️ Obfuscating Filename: {original_name} -> {name}")

        ArchiveManager.run_archive_job(
            target_path,
            name,
            conf.get('split', '1024M'),
            conf.get('password'),
            conf.get('format', 'rar'),
            True, # Create Par2
            False, # No auto-upload in manager
            None, "",
            conf.get('naming', 'part1'),
            conf.get('recovery', True)
        )

        # Scan for output files (RAR/PAR2) in the parent dir
        parent = os.path.dirname(target_path)
        output_files = []

        for f in os.listdir(parent):
            if f.startswith(name) and (f.endswith('.rar') or f.endswith('.par2')):
                output_files.append(os.path.join(parent, f))

        if not output_files:
            raise Exception("Packer finished but no output files found!")

        log(f"Packer generated {len(output_files)} files.")
        return output_files

    @staticmethod
    def _step_gh_publish(files, conf, meta):
        """
        Publishes files to GitHub. Returns list of asset objects.
        Uses meta['tree_text'] for release body (Base64).
        """
        repo = conf.get('repo')
        tag_template = conf.get('tag_template', 'v{date}_{name}')

        # Obfuscation Logic
        obfuscate_title = conf.get('obfuscate_title', False)

        # Generate Tag
        date_str = datetime.now().strftime("%Y%m%d")

        raw_title = meta.get('title', 'upload')
        title_slug = raw_title.replace(' ', '_')

        if obfuscate_title:
            # Base64 Encode Title
            title_b64 = base64.urlsafe_b64encode(raw_title.encode('utf-8')).decode('utf-8').rstrip('=')
            display_title = title_b64
            # Keep tag simple or obfuscated? Tag is public URL.
            # Usually safer to obfuscate tag too if title is hidden.
            tag_slug = title_b64
        else:
            display_title = raw_title
            tag_slug = title_slug

        tag_name = tag_template.replace('{date}', date_str).replace('{name}', tag_slug)

        # Body: Base64 Tree
        tree_b64 = base64.b64encode(meta.get('tree_text', '').encode('utf-8')).decode('utf-8')
        body = f"Auto-Upload via ParFix.\n\n**Original Structure (Base64):**\n`{tree_b64}`\n\n**Stats:**\nSize: {WorkflowManager._human_size(meta.get('total_size', 0))}\nFiles: {meta.get('file_count', 0)}"

        # Use GitHubManager to publish (We need a method that returns assets!)
        # Existing run_publish_job is void. We need to call internal methods.

        acc_id = "1" # TODO: Pass from config or context
        # For now, let's use the first available account or require one in config
        # Assuming GitHubManager has logic.

        # Create Release
        # NOTE: We need to import GitHubManager static methods.
        # Assuming user provided account_id in config
        account_id = conf.get('account_id')

        # 1. Create Release
        token = GitHubManager._get_token_for_account(account_id)
        if not token: raise Exception("No GitHub Account selected for Publish")

        # Create Release API call (simplified reuse)
        clean_repo = repo.replace('https://github.com/', '').strip('/')
        create_url = f"https://api.github.com/repos/{clean_repo}/releases"
        headers = {'Authorization': f'token {token}', 'Accept': 'application/vnd.github.v3+json'}
        payload = {"tag_name": tag_name, "name": display_title, "body": body}

        import requests
        r = requests.post(create_url, json=payload, headers=headers)
        if r.status_code not in [200, 201]:
             raise Exception(f"Release Create Failed: {r.text}")

        release_data = r.json()
        upload_url_template = release_data['upload_url']

        # 2. Upload Assets
        assets_out = []
        for file_path in files:
            fname = os.path.basename(file_path)
            log(f"Uploading {fname}...")
            upload_url = upload_url_template.split('{')[0] + f"?name={fname}"
            with open(file_path, 'rb') as f:
                h = headers.copy()
                h['Content-Type'] = 'application/octet-stream'
                ru = requests.post(upload_url, data=f, headers=h)
                if ru.status_code not in [200, 201]:
                    log(f"Failed to upload {fname}")
                else:
                    adata = ru.json()
                    assets_out.append({
                        'name': fname,
                        'size': os.path.getsize(file_path),
                        'url': adata['browser_download_url'] # Or api url? For JDownloader browser url is better
                    })

        return assets_out

    @staticmethod
    def _step_catalog(context, conf):
        """
        Adds entry to catalog using context data.
        Handles Smart Cover Image and No-Cover tags.
        """
        cm = CatalogManager()

        assets = context.get('github_assets', [])
        meta = context.get('meta', {})

        # Calculate compressed size
        comp_size = sum(a['size'] for a in assets)

        tags = ['Auto-Indexed']

        # Handle Cover Image
        image_path = None
        if meta.get('cover_image'):
            # Copy/Optimize image to Catalog Assets
            # We assume cover_image is a local path
            try:
                # We need to open it as a file object for CatalogManager.save_image
                # CatalogManager expects a FileStorage-like object usually (from Flask)
                # OR we can modify save_image to accept a path?
                # Actually save_image calls .save(path) or Image.open(file_obj).
                # Image.open(path) works fine!
                # But save_image calls file_obj.filename to get extension.
                # Let's create a dummy object wrapper or just pass the path if we overload save_image?
                # No, simpler: Open it in binary mode.
                with open(meta['cover_image'], 'rb') as f:
                    # Mock Flask FileStorage attribute
                    f.filename = os.path.basename(meta['cover_image'])
                    image_path = cm.save_image(f, optimize=True)
                    log(f"✅ Processed Cover Image: {image_path}")
            except Exception as e:
                log(f"❌ Failed to process cover image: {e}")

        if meta.get('missing_cover'):
            tags.append('No-Cover')

        entry = cm.create_entry(
            title=meta.get('title', 'Unknown'),
            file_name=f"{len(assets)} Archives",
            file_size=comp_size,
            url=f"https://github.com/{conf.get('repo')}",
            category=conf.get('category', 'General'),
            tags=tags,
            assets=assets,
            image=image_path,
            priority=int(conf.get('priority', 1))
        )
        cm.add_entry(entry)
        log(f"Added to Catalog: {entry['title']}")

    @staticmethod
    def _human_size(size):
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024: return f"{size:.2f} {unit}"
            size /= 1024
        return f"{size:.2f} TB"
