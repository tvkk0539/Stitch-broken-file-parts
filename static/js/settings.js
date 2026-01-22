async function loadSettings() {
     const res = await fetch('/api/settings');
     const data = await res.json();
     document.getElementById('set-gh-token').value = data.github_token||'';
     document.getElementById('set-discord').value = data.discord_webhook||'';
     document.getElementById('set-tg-token').value = data.telegram_token||'';
     document.getElementById('set-tg-chat').value = data.telegram_chat_id||'';
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
                telegram_chat_id: document.getElementById('set-tg-chat').value
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
