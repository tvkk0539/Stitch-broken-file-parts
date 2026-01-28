import json
import os
import uuid
from app.managers.sync import SyncManager
from datetime import datetime

class ProfileManager:
    """
    Manages Publishing Strategy Profiles.
    Stored in profiles.json.
    """
    def __init__(self):
        self.primary_dir = SyncManager.DATA_DIR
        self.fallback_dir = "."
        self.filename = "profiles.json"
        self.path = self._resolve_path(self.filename)
        self.profiles = self.load_profiles()

    def _resolve_path(self, filename):
        if SyncManager.is_configured():
            return os.path.join(self.primary_dir, filename)
        return os.path.join(self.fallback_dir, filename)

    def load_profiles(self):
        if not os.path.exists(self.path): return []
        try:
            with open(self.path, 'r') as f: return json.load(f)
        except: return []

    def save_profiles(self):
        try:
            with open(self.path, 'w') as f:
                json.dump(self.profiles, f, indent=2)
            if SyncManager.is_configured():
                SyncManager.push_data("Updated profiles.json")
            return True
        except: return False

    def get_all(self):
        return self.profiles

    def get_by_id(self, pid):
        return next((p for p in self.profiles if p['id'] == pid), None)

    def create_profile(self, name, config):
        p = {
            "id": str(uuid.uuid4()),
            "name": name,
            "config": config,
            "created_at": datetime.now().isoformat()
        }
        self.profiles.append(p)
        self.save_profiles()
        return p

    def update_profile(self, pid, name, config):
        for p in self.profiles:
            if p['id'] == pid:
                p['name'] = name
                p['config'] = config
                self.save_profiles()
                return p
        return None

    def delete_profile(self, pid):
        self.profiles = [p for p in self.profiles if p['id'] != pid]
        self.save_profiles()
        return True
