let ghActiveAccount = null;

function openGitHubApp() {
    switchView('gh-app');
    loadGhAccounts();
    // Default to Account Hub state
    ghSwitchAccount();
}

async function loadGhAccounts() {
    const grid = document.getElementById('gh-accounts-grid');
    grid.innerHTML = '<div style="color:var(--text-muted);">Loading accounts...</div>';

    try {
        const res = await fetch('/api/apps/github/accounts');
        const accounts = await res.json();

        grid.innerHTML = '';
        if(accounts.length === 0) {
            grid.innerHTML = '<div style="grid-column: 1/-1; text-align:center; padding:30px; color:var(--text-muted); border:1px dashed var(--border-color); border-radius:8px;">No accounts connected. Add one to get started.</div>';
            return;
        }

        accounts.forEach(acc => {
            const card = document.createElement('div');
            card.className = 'app-card';
            card.style.flexDirection = 'row';
            card.style.height = 'auto';
            card.style.padding = '15px';
            card.style.justifyContent = 'space-between';

            card.innerHTML = `
                <div style="display:flex; align-items:center; gap:15px; flex:1;">
                    <img src="${acc.avatar_url || 'https://github.com/identicons/user.png'}" style="width:40px; height:40px; border-radius:50%; background:#000;">
                    <div style="text-align:left;">
                        <div style="font-weight:bold; color:#c0caf5;">${acc.username}</div>
                        <div style="font-size:0.8em; color:var(--text-muted);">${acc.name || ''}</div>
                    </div>
                </div>
                <div style="display:flex; flex-direction:column; gap:5px;">
                    <button class="secondary" style="padding:5px 10px; font-size:0.8em;" onclick="ghSelectAccount('${acc.id}', '${acc.username}', '${acc.avatar_url}')">Select</button>
                    <button class="danger" style="padding:5px 10px; font-size:0.8em; background:none; border:1px solid var(--error-color); color:var(--error-color);" onclick="ghLogout('${acc.id}', event)">Remove</button>
                </div>
            `;
            grid.appendChild(card);
        });

    } catch(e) {
        grid.innerHTML = 'Error loading accounts.';
    }
}

function ghSelectAccount(id, username, avatar) {
    ghActiveAccount = {id, username};
    document.getElementById('gh-state-accounts').style.display = 'none';
    document.getElementById('gh-state-tools').style.display = 'block';

    // Update Header
    const display = document.getElementById('gh-active-user-display');
    display.style.display = 'flex';
    document.getElementById('gh-active-username').textContent = username;
    document.getElementById('gh-active-avatar').src = avatar || 'https://github.com/identicons/user.png';

    // Auto-fetch repos
    switchGhTab('repos');
    fetchMyRepos();
}

function ghSwitchAccount() {
    ghActiveAccount = null;
    document.getElementById('gh-state-accounts').style.display = 'block';
    document.getElementById('gh-state-tools').style.display = 'none';
    document.getElementById('gh-active-user-display').style.display = 'none';
}

async function ghLogout(id, e) {
    if(e) e.stopPropagation();
    if(confirm("Remove this account?")) {
        await fetch('/api/apps/github/logout', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({id})});
        loadGhAccounts();
    }
}

// Login Modal Handlers
document.addEventListener('DOMContentLoaded', () => {
    const ghLoginModal = document.getElementById('gh-login-modal');
    window.openGhLoginModal = function() { ghLoginModal.style.display = 'block'; }

    document.getElementById('cancel-gh-login').onclick = () => ghLoginModal.style.display='none';
    document.getElementById('confirm-gh-login').onclick = async () => {
        const token = document.getElementById('gh-login-token').value.trim();
        if(!token) return showToast('Token required', 'error');

        const btn = document.getElementById('confirm-gh-login');
        btn.disabled = true; btn.textContent = 'Verifying...';

        try {
            const res = await fetch('/api/apps/github/login', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({token})});
            const data = await res.json();
            if(data.error) throw new Error(data.error);

            showToast(`Logged in as ${data.username}`, 'success');
            document.getElementById('gh-login-token').value = '';
            ghLoginModal.style.display = 'none';
            loadGhAccounts();
        } catch(e) {
            showToast(e.message, 'error');
        } finally {
            btn.disabled = false; btn.textContent = 'Verify & Login';
        }
    };
});

function switchGhTab(tab) {
    document.querySelectorAll('.gh-tab').forEach(e => e.classList.remove('active'));
    document.getElementById(`gh-tab-${tab}`).classList.add('active');
    document.getElementById('gh-view-repos').style.display = tab==='repos' ? 'block' : 'none';
    document.getElementById('gh-view-down').style.display = tab==='down' ? 'block' : 'none';
    document.getElementById('gh-view-pub').style.display = tab==='pub' ? 'block' : 'none';
}

async function fetchMyRepos() {
    const grid = document.getElementById('gh-repos-grid');
    grid.innerHTML = '<div style="color:var(--text-muted); grid-column:1/-1; text-align:center;">Loading repositories...</div>';

    try {
        const res = await fetch(`/api/apps/github/user/repos?account_id=${ghActiveAccount.id}`);
        const repos = await res.json();

        if(repos.error) throw new Error(repos.error);

        grid.innerHTML = '';
        if(repos.length === 0) {
            grid.innerHTML = '<div style="color:var(--text-muted); grid-column:1/-1;">No repositories found.</div>';
            return;
        }

        repos.forEach(repo => {
            const card = document.createElement('div');
            card.className = 'app-card';
            card.style.height = 'auto';
            card.style.textAlign = 'left';
            card.style.alignItems = 'flex-start';
            card.style.padding = '15px';

            const visibilityIcon = repo.private ? '🔒' : '🌍';
            const visibilityColor = repo.private ? '#e0af68' : '#9ece6a'; // Gold vs Green

            card.innerHTML = `
                <div style="display:flex; justify-content:space-between; width:100%; margin-bottom:10px;">
                    <div style="font-weight:bold; color:#c0caf5; word-break:break-all;">${repo.name}</div>
                    <div style="font-size:0.9em; color:${visibilityColor};" title="${repo.private ? 'Private' : 'Public'}">${visibilityIcon}</div>
                </div>
                <div style="font-size:0.8em; color:var(--text-muted); margin-bottom:15px;">
                    ⭐ ${repo.stars} &nbsp;•&nbsp; Updated ${new Date(repo.updated_at).toLocaleDateString()}
                </div>
                <div style="display:flex; gap:8px; flex-wrap:wrap; width:100%;">
                    <button class="secondary" style="flex:1; font-size:0.8em; padding:6px;" onclick="ghSelectRepo('${repo.name}', 'down')">Download</button>
                    <button class="purple-btn" style="flex:1; font-size:0.8em; padding:6px;" onclick="ghSelectRepo('${repo.name}', 'pub')">Publish</button>
                </div>
                <div style="margin-top:10px; width:100%;">
                    <button class="icon-btn" style="width:100%; font-size:0.8em; border:1px solid var(--border-color); color:var(--text-muted);" onclick="ghToggleVisibility('${repo.name}', ${repo.private})">
                        ${repo.private ? 'Make Public' : 'Make Private'}
                    </button>
                </div>
            `;
            grid.appendChild(card);
        });

    } catch(e) {
        grid.innerHTML = `<div style="color:var(--error-color); grid-column:1/-1;">Error: ${e.message}</div>`;
    }
}

function ghSelectRepo(name, tab) {
    switchGhTab(tab);
    if(tab === 'down') {
        document.getElementById('gh-repo-input').value = name;
        fetchGhReleases(); // Auto fetch
    } else {
        document.getElementById('gh-pub-repo').value = name;
    }
}

async function ghToggleVisibility(name, isPrivate) {
    const action = isPrivate ? "PUBLIC" : "PRIVATE";
    const confirmMsg = isPrivate
        ? `⚠️ WARNING ⚠️\n\nThis will make '${name}' PUBLIC to the entire internet.\nAnyone can see your code.\n\nAre you sure?`
        : `Make '${name}' Private?`;

    if(!confirm(confirmMsg)) return;

    try {
        const res = await fetch('/api/apps/github/repo/visibility', {
            method:'POST',
            headers:{'Content-Type':'application/json'},
            body:JSON.stringify({
                repo: name,
                private: !isPrivate,
                account_id: ghActiveAccount.id
            })
        });
        const data = await res.json();
        if(data.error) throw new Error(data.error);

        showToast(`Repo is now ${data.private ? 'Private' : 'Public'}`, 'success');
        fetchMyRepos(); // Refresh list
    } catch(e) {
        showToast(e.message, 'error');
    }
}

async function fetchGhReleases() {
    const repo = document.getElementById('gh-repo-input').value;
    const ghResults = document.getElementById('gh-results');
    if(!repo) return showToast('Enter Repo', 'error');

    ghResults.innerHTML = '<div style="text-align:center; padding:20px; color:var(--text-muted);">Fetching releases...</div>';
    document.getElementById('gh-results-header').style.display = 'none';

    try {
        // Pass account_id if available
        const body = { repo };
        if(ghActiveAccount) body.account_id = ghActiveAccount.id;

        const res = await fetch('/api/apps/github/releases', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
        const data = await res.json();
        if(data.error) throw new Error(data.error);

        document.getElementById('gh-results-header').style.display = 'block';
        document.getElementById('gh-results-header').innerHTML = `Latest Release: <span style="color:#c0caf5;">${data.name}</span> <span style="font-size:0.8em; color:var(--text-muted);">(${data.tag})</span>`;

        ghResults.innerHTML = '';
        if(!data.assets || data.assets.length === 0) {
                ghResults.innerHTML = '<div style="padding:10px;">No assets found in this release.</div>';
                return;
        }

        data.assets.forEach(asset => {
            const div = document.createElement('div'); div.className = 'gh-result-item';
            div.innerHTML = `
                <div style="display:flex; align-items:center; gap:10px;">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="color:#565f89"><path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"></path><polyline points="13 2 13 9 20 9"></polyline></svg>
                    <div>
                        <div style="font-weight:bold; color:#c0caf5;">${asset.name}</div>
                        <div style="font-size:0.8em; color:var(--text-muted);">${formatBytes(asset.size)}</div>
                    </div>
                </div>
                <button class="icon-btn" style="color:var(--success-color); border:1px solid #2f3549; padding:5px 10px; border-radius:4px;" title="Download to VPS">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>
                </button>
            `;
            div.querySelector('button').onclick = () => downloadGhAsset(asset.download_url, asset.name);
            ghResults.appendChild(div);
        });
    } catch(e) {
        ghResults.innerHTML = `<div style="color:var(--error-color); padding:10px; border:1px solid var(--error-color); border-radius:4px;">Error: ${e.message}</div>`;
    }
}

async function downloadGhAsset(url, filename) {
    const sub = prompt(`Download ${filename} to folder:`, 'Downloads/');
    if(sub === null) return;

    // Pass account_id
    const body = { url, filename, path:sub };
    if(ghActiveAccount) body.account_id = ghActiveAccount.id;

    await fetch('/api/apps/github/download', {
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify(body)
    });
    showToast('Download Queued', 'success');
}

// Publisher
function openFilePickerForGh() {
    // Check if user selected a file in the main view
    const ghPubFile = document.getElementById('gh-pub-file');
    if(selectedPaths.length === 1 && browserMode === 'local') {
        ghPubFile.value = selectedPaths[0];
        showToast('File selected from browser', 'success');
    } else {
        alert("Please go to the 'Files' tab, select ONE local file, then come back here and click this button.");
    }
}

async function triggerGhPublish() {
    const ghPubFile = document.getElementById('gh-pub-file');
    const ghPubRepo = document.getElementById('gh-pub-repo');
    const ghPubTag = document.getElementById('gh-pub-tag');
    const ghPubBody = document.getElementById('gh-pub-body');
    const ghPubPrerelease = document.getElementById('gh-pub-prerelease');
    const ghPubDraft = document.getElementById('gh-pub-draft');

    if(!ghPubFile.value) return showToast('Select a file first', 'error');
    if(!ghActiveAccount) return showToast('No active account', 'error');

    await fetch('/api/apps/github/publish', {
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify({
            repo: ghPubRepo.value,
            tag: ghPubTag.value,
            file_path: ghPubFile.value,
            account_id: ghActiveAccount.id,
            body: ghPubBody.value,
            prerelease: ghPubPrerelease.checked,
            draft: ghPubDraft.checked
        })
    });
    showToast('Publish Queued', 'success');
}
