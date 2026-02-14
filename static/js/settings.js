async function loadSettings() {
     const res = await fetch('/api/settings');
     const data = await res.json();
     document.getElementById('set-gh-token').value = data.github_token||'';
     document.getElementById('set-discord').value = data.discord_webhook||'';
     document.getElementById('set-tg-token').value = data.telegram_token||'';
     document.getElementById('set-tg-chat').value = data.telegram_chat_id||'';

     // Backup settings
     document.getElementById('set-backup-repo').value = data.backup_repo_url || '';
     document.getElementById('set-backup-token').value = data.backup_token || '';

     // Fetch Sync Status
     updateSyncStatusUI();
}

async function updateSyncStatusUI() {
    try {
        const res = await fetch('/api/sync/status');
        const data = await res.json();

        const container = document.getElementById('sync-status-container');
        // Ensure container exists if not injected yet
        if (!container) {
            const parent = document.getElementById('set-backup-repo').parentElement.parentElement;
            const div = document.createElement('div');
            div.id = 'sync-status-container';
            div.style.marginBottom = '15px';
            parent.insertBefore(div, parent.querySelector('.form-group')); // Insert before inputs
        }

        const statusDiv = document.getElementById('sync-status-container');
        const btn = document.querySelector('button[onclick="triggerDataSyncInit()"]');
        const repoInput = document.getElementById('set-backup-repo');
        const tokenInput = document.getElementById('set-backup-token');

        if (data.configured) {
            statusDiv.innerHTML = `
                <div style="background:rgba(76, 175, 80, 0.1); border:1px solid #4CAF50; color:#4CAF50; padding:10px; border-radius:4px; display:flex; align-items:center; gap:10px;">
                    <span style="font-size:1.2em;">✅</span>
                    <div>
                        <strong>Connected</strong><br>
                        <span style="font-size:0.8em; font-family:monospace;">${data.remote_url || 'Unknown Remote'}</span>
                    </div>
                </div>
            `;

            // Disable Inputs to prevent accidental overwrite
            repoInput.disabled = true;
            tokenInput.disabled = true;
            repoInput.style.opacity = '0.6';
            tokenInput.style.opacity = '0.6';

            // Change Button to Destructive Re-Link
            if(btn) {
                btn.textContent = "⚠️ Re-Link (Overwrite Local Data)";
                btn.className = "danger"; // Use danger class
                btn.onclick = () => triggerDataSyncInit(true); // Pass flag
            }

        } else {
            statusDiv.innerHTML = `
                <div style="background:rgba(244, 67, 54, 0.1); border:1px solid #f44336; color:#f44336; padding:10px; border-radius:4px; display:flex; align-items:center; gap:10px;">
                    <span style="font-size:1.2em;">🔴</span>
                    <div>
                        <strong>Not Connected</strong><br>
                        <span style="font-size:0.8em;">Data is stored locally only.</span>
                    </div>
                </div>
            `;
            repoInput.disabled = false;
            tokenInput.disabled = false;
            repoInput.style.opacity = '1';
            tokenInput.style.opacity = '1';

            if(btn) {
                btn.textContent = "Link & Pull Data";
                btn.className = "secondary";
                btn.onclick = () => triggerDataSyncInit(false);
            }
        }
    } catch(e) { console.error("Sync Status Error", e); }
}

async function triggerDataSyncInit(isRelink = false) {
    if (isRelink) {
        if (!confirm("⚠️ WARNING: You are already connected!\n\nRe-linking will DELETE your current local database and replace it with the version from GitHub.\n\nAny unsynced local changes will be LOST.\n\nAre you sure you want to proceed?")) {
            return;
        }
        // Enable inputs temporarily so we can read values if user wants to change them?
        // Actually, if re-linking, they might want to change repo.
        // We should enable them if they click re-link?
        // Logic: If they click Re-Link, we probably just execute with CURRENT values in inputs?
        // But inputs are disabled.
        // Better UX: If connected, Re-Link button enables inputs first?
        // For now, let's assume they want to use what's in the box (or they can refresh).
        // Actually, to change repo, they need to edit inputs.
        // Let's make "Re-Link" unlock inputs first?

        // Revised Logic: If inputs disabled, first click unlocks them. Second click executes.
        const repoInput = document.getElementById('set-backup-repo');
        if (repoInput.disabled) {
            repoInput.disabled = false;
            document.getElementById('set-backup-token').disabled = false;
            repoInput.style.opacity = '1';
            document.getElementById('set-backup-token').style.opacity = '1';

            const btn = document.querySelector('button[onclick*="triggerDataSyncInit"]');
            btn.textContent = "Confirm Re-Link (Destructive)";
            return; // Stop here, let user edit
        }
    }

    const repo = document.getElementById('set-backup-repo').value;
    const token = document.getElementById('set-backup-token').value;

    if(!repo || !token) {
        alert("Please provide both Repo URL and Token for backup.");
        return;
    }

    // Do NOT trigger save-set click, as it might overwrite config if fields are empty.
    // We send repo/token directly to init.

    try {
        showToast("Linking Repository... please wait.");
        const res = await fetch('/api/sync/init', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ repo_url: repo, token: token })
        });
        const data = await res.json();
        if(data.status === 'success') {
            showToast("Success: Repository Linked!");
            // Refresh catalog since we might have pulled new data
            if(window.catalog) window.catalog.reload();
            // Reload settings to ensure we see the saved repo/token
            loadSettings();
        } else {
            alert("Sync Error: " + data.message);
        }
    } catch(e) {
        alert("Request Failed: " + e);
    }
}

async function triggerDataSyncPush() {
    try {
        showToast("Pushing backup...");
        const res = await fetch('/api/sync/push', { method: 'POST' });
        const data = await res.json();
        if(data.status === 'success') {
            showToast("Backup Pushed Successfully!");
        } else {
            alert("Push Error: " + data.message);
        }
    } catch(e) {
        alert("Request Failed: " + e);
    }
}

// Upload Config
document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('save-set').onclick = async () => {
        await fetch('/api/settings', {
            method:'POST',
            headers:{'Content-Type':'application/json'},
            body:JSON.stringify({
                github_token: document.getElementById('set-gh-token').value,
                discord_webhook: document.getElementById('set-discord').value,
                telegram_token: document.getElementById('set-tg-token').value,
                telegram_chat_id: document.getElementById('set-tg-chat').value,
                backup_repo_url: document.getElementById('set-backup-repo').value,
                backup_token: document.getElementById('set-backup-token').value
            })
        });
        showToast('Settings Saved', 'success');
    };

    document.getElementById('upload-config-btn').onclick = async () => {
        const f = document.getElementById('config-file-input').files[0];
        if(!f) return;
        const fd = new FormData(); fd.append('file', f);
        const res = await fetch('/api/settings/upload-config', {method:'POST', body:fd});
        const d = await res.json();
        if(d.status==='uploaded') showToast('Config Uploaded', 'success');
        else showToast('Error', 'error');
    };
});
