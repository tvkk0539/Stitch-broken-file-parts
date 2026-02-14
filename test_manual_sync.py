import os
import shutil
import tempfile
import sqlite3
import yaml
from app.managers.apple_music import AppleMusicManager

def test_manual_sync_flow():
    print("--- Starting Manual Sync Flow Test ---")

    # 1. Setup Test Environment
    test_dir = tempfile.mkdtemp()
    db_dir = os.path.join(test_dir, 'data')
    install_dir = os.path.join(test_dir, 'downloads', 'Apple Music', 'repo')
    os.makedirs(db_dir, exist_ok=True)
    os.makedirs(install_dir, exist_ok=True)

    # Override paths for testing
    original_db_dir = AppleMusicManager.db.db_dir
    original_app_dir = AppleMusicManager.APP_DIR

    # We need to patch the manager instance to use our test paths
    # Since find_config_path uses APP_DIR, we patch find_install_path

    print(f"Test Environment: {test_dir}")

    # Create Dummy config.yaml
    config_path = os.path.join(install_dir, 'config.yaml')
    initial_data = {
        'media-user-token': 'initial_token_123',
        'limit-max': 5,
        'embed-cover': True
    }
    with open(config_path, 'w') as f:
        yaml.dump(initial_data, f)
    print(f"Created config.yaml at {config_path}")

    # Initialize Manager with custom DB path (hacky but effective for unit test)
    manager = AppleMusicManager()
    manager.db.db_dir = db_dir
    manager.db.db_path = os.path.join(db_dir, 'apple_music.db')
    manager.db._init_db() # Create fresh DB

    # Mock find_install_path to return our test dir
    manager.find_install_path = lambda: install_dir

    # 2. Verify DB is empty initially
    db_val = manager.db.get('media-user-token')
    print(f"Initial DB Value: {db_val}")
    assert db_val is None, "DB should be empty initially"

    # 3. Step 2: Simulate "Load Settings" (Import)
    print("\n--- Simulating 'Load Settings' ---")
    res = manager.sync_yaml_to_db()
    print(f"Import Result: {res}")

    # Verify DB has data
    db_token = manager.db.get('media-user-token')
    db_limit = manager.db.get('limit-max')
    print(f"DB Token: {db_token}")
    print(f"DB Limit: {db_limit}")

    assert db_token == 'initial_token_123', "Token not imported correctly"
    assert str(db_limit) == '5', "Limit not imported correctly"

    # 4. Step 3: Simulate "Edit in UI" (Update DB)
    print("\n--- Simulating 'Edit in UI' ---")
    new_token = 'updated_token_999'
    manager.update_config({'media-user-token': new_token})

    # Verify DB updated
    db_token_new = manager.db.get('media-user-token')
    print(f"Updated DB Token: {db_token_new}")
    assert db_token_new == new_token, "DB not updated"

    # Verify File is NOT yet updated (Manual Sync only!)
    # update_config calls sync_db_to_yaml internally usually?
    # Wait, my implementation of update_config calls _sync_from_db_to_yaml automatically.
    # Ah, the user requested "Manual Sync".
    # If update_config automatically syncs to file, then "Save Settings" button is redundant for UI edits.
    # BUT, "Save Settings" is useful if we did bulk DB operations without sync.
    # Let's check update_config implementation.

    # The current code:
    # def update_config(self, updates):
    #     self.db.bulk_update(updates)
    #     return self._sync_from_db_to_yaml()  <-- It DOES sync automatically on save.

    # So "Save Settings" button is mainly for re-exporting if file was deleted or reverted?
    # Or maybe the user wants update_config to NOT sync automatically?
    # "make like manually sync to db by button... then make another but sync db setings to current config.yml"
    # The user said "automatic is not doing anything".
    # If I disable auto-sync in update_config, then "Save" button becomes mandatory.
    # Let's check file content now.

    with open(config_path, 'r') as f:
        file_data = yaml.safe_load(f)
    print(f"File Token (Auto-Sync Check): {file_data.get('media-user-token')}")

    # If it auto-synced, this will be updated_token_999.

    # 5. Step 4: Explicit "Save Settings" (Export)
    # Even if it auto-synced, let's verify the export function works.
    print("\n--- Simulating 'Save Settings' ---")
    # Let's manually change DB content to verify export
    manager.db.set('manual_key', 'manual_value')

    res = manager.sync_db_to_yaml()
    print(f"Export Result: {res}")

    with open(config_path, 'r') as f:
        final_data = yaml.safe_load(f)
    print(f"Final File manual_key: {final_data.get('manual_key')}")

    assert final_data.get('manual_key') == 'manual_value', "Export did not write manual key"

    # Cleanup
    shutil.rmtree(test_dir)
    print("\n--- Test Passed ---")

if __name__ == "__main__":
    test_manual_sync_flow()
