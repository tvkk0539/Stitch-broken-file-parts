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
}

async function triggerDataSyncInit() {
    const repo = document.getElementById('set-backup-repo').value;
    const token = document.getElementById('set-backup-token').value;

    if(!repo || !token) {
        alert("Please provide both Repo URL and Token for backup.");
        return;
    }

    // Save first to ensure backend has them
    await document.getElementById('save-set').click();

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
            if(window.catalog) window.catalog.load();
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
