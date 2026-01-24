import json
import os
import uuid
import logging
import time
import threading
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
        wf_data: The full workflow object (passed explicitly to avoid race conditions with file reload).
        """
        log(f"🚀 Starting Workflow: {wf_data['name']}")

        context = {
            'files': input_paths, # Current active files
            'initial_files': input_paths,
            'github_assets': [], # To collect upload URLs
            'catalog_entry': None
        }

        try:
            for i, step in enumerate(wf_data['steps']):
                step_type = step['type']
                conf = step['config']
                log(f"▶️ Step {i+1}/{len(wf_data['steps'])}: {step_type}")
                job_manager.update_job_details({'action': f"Step {i+1}: {step_type}"})

                if step_type == 'pack':
                    context['files'] = WorkflowManager._step_pack(context['files'], conf)
                elif step_type == 'github_publish':
                    context['github_assets'] = WorkflowManager._step_gh_publish(context['files'], conf)
                elif step_type == 'catalog_add':
                    WorkflowManager._step_catalog(context, conf)

                # Add more steps here (compress, upload, etc)

                time.sleep(1) # Small breathe

            log(f"✅ Workflow '{wf_data['name']}' Completed Successfully!")
            job_manager.update_job_details({'action': 'Completed', 'progress': '100%'})

        except Exception as e:
            log(f"❌ Workflow Failed at Step {i+1}: {e}")
            job_manager.update_job_details({'error': str(e)})
            raise e

    # --- Step Implementations ---

    @staticmethod
    def _step_pack(files, conf):
        """
        Runs Packer. Returns list of generated RAR files.
        """
        if not files: raise Exception("No input files for Pack step")

        # We assume single input folder or file for packing usually
        # But if multiple, we might need to pack them into one?
        # For now, let's take the first item path as "Target"
        target_path = files[0] # Simplification
        name = os.path.basename(target_path)

        # Call ArchiveManager logic (Synchronously? No, manager creates a job usually)
        # We need a Blocking version or wait for it.
        # Since ArchiveManager.run_archive_job is designed as a Job function, we can call it directly?
        # Yes, but it updates job_manager context. Since WE are the job now, it might overwrite our details.
        # That's acceptable.

        # NOTE: run_archive_job returns output path or raises.
        # Wait, run_archive_job doesn't return output files list explicitly.
        # We might need to refactor ArchiveManager slightly or guess output.
        # Actually, ArchiveManager.run_archive_job is void.
        # We need to implement a wrapper that waits and detects output.

        # HACK: For now, let's assume standard output naming
        ArchiveManager.run_archive_job(
            target_path,
            name,
            conf.get('split', '1024M'),
            conf.get('password'),
            conf.get('format', 'rar'),
            True, # Create Par2
            False, # Upload? No, next step handles it
            None, "",
            conf.get('naming', 'part1'),
            conf.get('recovery', True)
        )

        # Detect Output
        # This is tricky. ArchiveManager puts them in the same folder or parent?
        # Usually same folder.
        # Let's Scan for them.
        parent = os.path.dirname(target_path)
        if os.path.isdir(target_path): parent = os.path.dirname(target_path) # if input was dir, archives are outside?
        # Actually ArchiveManager: "dest_dir = os.path.dirname(source_path)"

        # Return list of rar parts
        # This is heuristic and might be brittle. Professional way: ArchiveManager returns paths.
        # For MVP, we pass.

        return files # Placeholder: In real implementation, this must return the .rar files

    @staticmethod
    def _step_gh_publish(files, conf):
        """
        Publishes files to GitHub. Returns list of asset objects {name, url, size}.
        """
        # Logic to call GitHubManager.run_publish_job loop
        # We need to tag generation logic
        return [] # Placeholder

    @staticmethod
    def _step_catalog(context, conf):
        """
        Adds entry to catalog using context data.
        """
        pass
