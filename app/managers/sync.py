import os
import subprocess
import logging
import shutil

logger = logging.getLogger(__name__)

class SyncManager:
    """
    Manages synchronization of the 'data/' folder with a Private GitHub Repository.
    This ensures 'catalog.json' is backed up offsite.
    """

    DATA_DIR = "data"

    @staticmethod
    def _run_git(args, cwd=None):
        """Helper to run git commands safely."""
        try:
            # Check if git is installed
            subprocess.run(["git", "--version"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            result = subprocess.run(
                ["git"] + args,
                cwd=cwd,
                capture_output=True,
                text=True,
                check=True
            )
            return True, result.stdout.strip()
        except subprocess.CalledProcessError as e:
            logger.error(f"Git Error: {e.stderr}")
            return False, e.stderr
        except Exception as e:
            logger.error(f"Sync Error: {str(e)}")
            return False, str(e)

    @staticmethod
    def is_configured():
        """Checks if the data directory is a valid git repo."""
        return os.path.exists(os.path.join(SyncManager.DATA_DIR, ".git"))

    @staticmethod
    def init_sync(repo_url, token):
        """
        Clones the private repo into the data/ folder.
        Handles auth by embedding token: https://<token>@github.com/...
        """
        if not repo_url or not token:
            return False, "Missing URL or Token"

        # Construct Auth URL
        # Assuming repo_url is like "https://github.com/user/repo.git"
        if "github.com" in repo_url and "@" not in repo_url:
            auth_url = repo_url.replace("https://", f"https://{token}@")
        else:
            auth_url = repo_url

        # Clean existing data dir if it's not a repo
        if os.path.exists(SyncManager.DATA_DIR):
            if not os.path.exists(os.path.join(SyncManager.DATA_DIR, ".git")):
                # Backup existing catalog.json if exists
                if os.path.exists(os.path.join(SyncManager.DATA_DIR, "catalog.json")):
                    shutil.move(os.path.join(SyncManager.DATA_DIR, "catalog.json"), "catalog.json.bak")
                shutil.rmtree(SyncManager.DATA_DIR)
            else:
                return False, "Data directory is already linked to a repository."

        # Clone
        success, msg = SyncManager._run_git(["clone", auth_url, SyncManager.DATA_DIR])

        if success:
            # Configure user for this repo (local config only)
            SyncManager._run_git(["config", "user.email", "parfix-bot@local"], cwd=SyncManager.DATA_DIR)
            SyncManager._run_git(["config", "user.name", "ParFix Bot"], cwd=SyncManager.DATA_DIR)
            return True, "Repository linked successfully."
        else:
            return False, f"Clone failed: {msg}"

    @staticmethod
    def pull_data():
        """Pulls latest changes from remote."""
        if not SyncManager.is_configured():
            return False, "Sync not configured."

        return SyncManager._run_git(["pull"], cwd=SyncManager.DATA_DIR)

    @staticmethod
    def push_data(message="Auto-update catalog"):
        """Commits and pushes changes."""
        if not SyncManager.is_configured():
            return False, "Sync not configured."

        # Add
        SyncManager._run_git(["add", "."], cwd=SyncManager.DATA_DIR)

        # Check if anything to commit
        status_ok, status_out = SyncManager._run_git(["status", "--porcelain"], cwd=SyncManager.DATA_DIR)
        if not status_out:
            return True, "Nothing to sync."

        # Commit
        commit_ok, commit_msg = SyncManager._run_git(["commit", "-m", message], cwd=SyncManager.DATA_DIR)
        if not commit_ok:
            return False, f"Commit failed: {commit_msg}"

        # Push
        push_ok, push_msg = SyncManager._run_git(["push"], cwd=SyncManager.DATA_DIR)
        if push_ok:
            return True, "Synced to cloud."
        else:
            return False, f"Push failed: {push_msg}"
