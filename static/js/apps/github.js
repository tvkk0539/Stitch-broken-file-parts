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

    // Add "New Repo" card first
    const newRepoBtn = `
        <div class="app-card" style="height:auto; justify-content:center; border-style:dashed; opacity:0.8;" onclick="openGhNewRepoModal()">
            <div style="font-size:2em; color:var(--accent-color);">+</div>
            <div>New Repository</div>
        </div>
    `;

    // Add "Import Repo" card
    const importRepoBtn = `
        <div class="app-card" style="height:auto; justify-content:center; border-style:dashed; opacity:0.8;" onclick="openGhImportModal()">
            <div style="font-size:2em; color:#bb9af7;">⬇️</div>
            <div>Import Repo</div>
        </div>
    `;

    try {
        const res = await fetch(`/api/apps/github/user/repos?account_id=${ghActiveAccount.id}`);
        const repos = await res.json();

        if(repos.error) throw new Error(repos.error);

        grid.innerHTML = newRepoBtn + importRepoBtn; // Start with buttons

        repos.forEach(repo => {
            const card = document.createElement('div');
            card.className = 'app-card';
            card.style.height = 'auto';
            card.style.textAlign = 'left';
            card.style.alignItems = 'flex-start';
            card.style.padding = '15px';

            const visibilityIcon = repo.private ? '🔒' : '🌍';
            const visibilityColor = repo.private ? '#e0af68' : '#9ece6a';

            card.innerHTML = `
                <div style="display:flex; justify-content:space-between; width:100%; margin-bottom:5px;">
                    <div style="font-weight:bold; color:#c0caf5; word-break:break-all;">${repo.name}</div>
                    <div style="font-size:0.9em; color:${visibilityColor};" title="${repo.private ? 'Private' : 'Public'}">${visibilityIcon}</div>
                </div>
                <div style="font-size:0.8em; color:var(--text-muted); margin-bottom:10px;">
                    ⭐ ${repo.stars} &nbsp;•&nbsp; ${new Date(repo.updated_at).toLocaleDateString()}
                </div>
                <div style="display:flex; gap:5px; flex-wrap:wrap; width:100%;">
                    <button class="secondary" style="flex:1; font-size:0.8em; padding:6px;" onclick="ghSelectRepo('${repo.name}', 'down')">Get</button>
                    <button class="purple-btn" style="flex:1; font-size:0.8em; padding:6px;" onclick="ghSelectRepo('${repo.name}', 'pub')">Pub</button>
                    <button class="info-btn" style="flex:0; font-size:0.8em; padding:6px;" onclick="ghOpenActions('${repo.name}')">▶</button>
                </div>
                <div style="margin-top:5px; width:100%; display:flex; gap:5px;">
                    <button class="icon-btn" style="flex:1; font-size:0.7em; border:1px solid var(--border-color); color:var(--text-muted);" onclick="ghToggleVisibility('${repo.name}', ${repo.private})">
                        ${repo.private ? 'Make Public' : 'Make Private'}
                    </button>
                    <button class="icon-btn" style="flex:0; font-size:0.7em; border:1px solid var(--border-color); color:var(--text-muted);" onclick="openGhRenameModal('${repo.name}')">✏️</button>
                    <button class="icon-btn" style="flex:0; font-size:0.7em; border:1px solid var(--error-color); color:var(--error-color);" onclick="ghDeleteRepo('${repo.name}')">🗑️</button>
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

// --- Create Repo Logic ---
function openGhNewRepoModal() {
    document.getElementById('gh-new-repo-modal').style.display = 'block';
}

document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('confirm-gh-create').onclick = async () => {
        const name = document.getElementById('gh-new-name').value;
        const desc = document.getElementById('gh-new-desc').value;
        const priv = document.getElementById('gh-new-private').checked;

        if(!name) return showToast('Name required', 'error');

        try {
            const res = await fetch('/api/apps/github/repo/create', {
                method:'POST',headers:{'Content-Type':'application/json'},
                body:JSON.stringify({name, description:desc, private:priv, account_id:ghActiveAccount.id})
            });
            const data = await res.json();
            if(data.error) throw new Error(data.error);

            showToast('Repository Created', 'success');
            document.getElementById('gh-new-repo-modal').style.display='none';
            fetchMyRepos();
        } catch(e) { showToast(e.message, 'error'); }
    };
});

// --- Import Repo Logic ---
function openGhImportModal() {
    document.getElementById('gh-import-repo-modal').style.display = 'block';
}

document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('confirm-gh-import').onclick = async () => {
        const sourceUrl = document.getElementById('gh-import-source').value;
        const targetName = document.getElementById('gh-import-target').value;
        const priv = document.getElementById('gh-import-private').checked;

        if(!sourceUrl || !targetName) return showToast('Source URL and Target Name required', 'error');

        try {
            const res = await fetch('/api/apps/github/repo/import', {
                method:'POST',headers:{'Content-Type':'application/json'},
                body:JSON.stringify({
                    source_url: sourceUrl,
                    target_name: targetName,
                    private: priv,
                    account_id: ghActiveAccount.id
                })
            });
            const data = await res.json();
            if(data.error) throw new Error(data.error);

            showToast('Import Job Queued', 'success');
            document.getElementById('gh-import-repo-modal').style.display='none';
            // Note: We don't fetchRepos immediately because it's a background job
        } catch(e) { showToast(e.message, 'error'); }
    };
});

// --- Clone Logic (In Downloader) ---
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

        // Header with Clone Actions (Top Level)
        const header = document.getElementById('gh-results-header');
        header.style.display = 'flex';
        header.style.justifyContent = 'space-between';
        header.style.alignItems = 'center';
        header.innerHTML = `
            <div>Found ${data.length} Releases</div>
            <button class="purple-btn" style="padding:5px 10px; font-size:0.8em;" onclick="triggerGhClone('${repo}')">Clone Source</button>
        `;

        ghResults.innerHTML = '';
        if(!data || data.length === 0) {
            ghResults.innerHTML = '<div style="padding:10px;">No releases found.</div>';
            return;
        }

        // Render Release Cards
        data.forEach((release, index) => {
            const releaseCard = document.createElement('div');
            releaseCard.style.background = 'var(--panel-bg)';
            releaseCard.style.border = '1px solid var(--border-color)';
            releaseCard.style.marginBottom = '10px';
            releaseCard.style.borderRadius = '6px';
            releaseCard.style.overflow = 'hidden';

            const isLatest = index === 0;
            const badge = isLatest ? '<span style="background:var(--success-color); color:#000; padding:2px 6px; border-radius:4px; font-size:0.7em; margin-left:8px; font-weight:bold;">LATEST</span>' : '';
            const preBadge = release.prerelease ? '<span style="background:var(--warning-color); color:#000; padding:2px 6px; border-radius:4px; font-size:0.7em; margin-left:8px; font-weight:bold;">PRE</span>' : '';
            const dateStr = new Date(release.published_at).toLocaleDateString();

            // Card Header (Clickable)
            const headerDiv = document.createElement('div');
            headerDiv.style.padding = '12px 15px';
            headerDiv.style.cursor = 'pointer';
            headerDiv.style.display = 'flex';
            headerDiv.style.justifyContent = 'space-between';
            headerDiv.style.alignItems = 'center';
            headerDiv.style.background = 'rgba(255,255,255,0.02)';

            headerDiv.innerHTML = `
                <div style="display:flex; align-items:center;">
                    <div style="font-weight:bold; color:#c0caf5; font-size:1.1em;">${release.tag}</div>
                    ${badge}
                    ${preBadge}
                </div>
                <div style="font-size:0.8em; color:var(--text-muted); display:flex; align-items:center; gap:10px;">
                    <span>${dateStr}</span>
                    <span style="transform: rotate(${isLatest?0:-90}deg); transition: transform 0.2s;" class="arrow-icon">▼</span>
                </div>
            `;

            // Assets Container
            const assetsDiv = document.createElement('div');
            assetsDiv.style.display = isLatest ? 'block' : 'none';
            assetsDiv.style.borderTop = '1px solid var(--border-color)';
            assetsDiv.style.padding = '10px';
            assetsDiv.style.background = '#13141c';

            headerDiv.onclick = () => {
                const isOpen = assetsDiv.style.display === 'block';
                assetsDiv.style.display = isOpen ? 'none' : 'block';
                headerDiv.querySelector('.arrow-icon').style.transform = isOpen ? 'rotate(-90deg)' : 'rotate(0deg)';
            };

            if(!release.assets || release.assets.length === 0) {
                assetsDiv.innerHTML = '<div style="padding:5px; color:var(--text-muted); font-size:0.9em;">No assets (Source code only).</div>';
            } else {
                release.assets.forEach(asset => {
                    const row = document.createElement('div');
                    row.className = 'gh-result-item'; // Reuse style
                    row.style.marginBottom = '5px';
                    row.innerHTML = `
                        <div style="display:flex; align-items:center; gap:10px;">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="color:#565f89"><path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"></path><polyline points="13 2 13 9 20 9"></polyline></svg>
                            <div>
                                <div style="color:#a9b1d6; font-size:0.95em;">${asset.name}</div>
                                <div style="font-size:0.75em; color:var(--text-muted);">${formatBytes(asset.size)}</div>
                            </div>
                        </div>
                        <button class="icon-btn" style="color:var(--success-color); border:1px solid #2f3549; padding:4px 8px; border-radius:4px;" title="Download">
                            ⬇️
                        </button>
                    `;
                    row.querySelector('button').onclick = (e) => {
                         e.stopPropagation();
                         downloadGhAsset(asset.download_url, asset.name);
                    };
                    assetsDiv.appendChild(row);
                });
            }

            releaseCard.appendChild(headerDiv);
            releaseCard.appendChild(assetsDiv);
            ghResults.appendChild(releaseCard);
        });

    } catch(e) {
        ghResults.innerHTML = `<div style="color:var(--error-color); padding:10px; border:1px solid var(--error-color); border-radius:4px;">Error: ${e.message}</div>`;
    }
}

async function triggerGhClone(repoName) {
    const sub = prompt(`Clone ${repoName} source code to folder:`, `Cloned/${repoName.split('/')[1]}`);
    if(!sub) return;

    // Construct full URL
    const url = `https://github.com/${repoName}.git`;

    await fetch('/api/apps/github/repo/clone', {
        method:'POST', headers:{'Content-Type':'application/json'},
        body:JSON.stringify({url, path:sub, account_id:ghActiveAccount.id})
    });
    showToast('Clone Queued', 'success');
}

// Rename Modal
let ghRenameTargetRepo = '';
function openGhRenameModal(repo) {
    ghRenameTargetRepo = repo;
    document.getElementById('gh-rename-source').textContent = repo;
    document.getElementById('gh-rename-input').value = repo.split('/')[1];
    document.getElementById('gh-rename-repo-modal').style.display='block';
}

async function ghDeleteRepo(repo) {
    const confirmMsg = `⚠️ DANGER ZONE ⚠️\n\nThis will DELETE '${repo}' PERMANENTLY.\nThis cannot be undone.\n\nType the repo name to confirm:`;
    const input = prompt(confirmMsg);
    if(input !== repo) {
        if(input) showToast('Mismatch, deletion cancelled', 'error');
        return;
    }

    const [owner, name] = repo.split('/');
    try {
        const res = await fetch('/api/apps/github/repo/delete', {
            method:'POST',headers:{'Content-Type':'application/json'},
            body:JSON.stringify({owner, repo:name, account_id:ghActiveAccount.id})
        });
        const data = await res.json();
        if(data.error) throw new Error(data.error);

        showToast('Repository Deleted', 'success');
        fetchMyRepos();
    } catch(e) { showToast(e.message, 'error'); }
}

document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('confirm-gh-rename').onclick = async () => {
        const newName = document.getElementById('gh-rename-input').value;
        const [owner, repo] = ghRenameTargetRepo.split('/');

        try {
            const res = await fetch('/api/apps/github/repo/rename', {
                method:'POST',headers:{'Content-Type':'application/json'},
                body:JSON.stringify({owner, repo, new_name:newName, account_id:ghActiveAccount.id})
            });
            const data = await res.json();
            if(data.error) throw new Error(data.error);

            showToast('Repository Renamed', 'success');
            document.getElementById('gh-rename-repo-modal').style.display='none';
            fetchMyRepos();
        } catch(e) { showToast(e.message, 'error'); }
    };
});

// --- Actions Logic ---
let ghActionsRepo = '';

async function ghOpenActions(repo) {
    ghActionsRepo = repo;
    document.getElementById('gh-actions-title').textContent = `Actions: ${repo}`;
    document.getElementById('gh-actions-modal').style.display = 'block';
    loadGhWorkflows();
    loadGhRuns();
}

async function loadGhWorkflows() {
    const el = document.getElementById('gh-workflows-list');
    el.innerHTML = 'Loading...';
    try {
        const res = await fetch('/api/apps/github/actions/workflows', {
            method:'POST',headers:{'Content-Type':'application/json'},
            body:JSON.stringify({repo:ghActionsRepo, account_id:ghActiveAccount.id})
        });
        const data = await res.json();
        if(data.error) throw new Error(data.error);

        el.innerHTML = '';
        data.forEach(wf => {
            const div = document.createElement('div');
            div.style.padding = '8px';
            div.style.borderBottom = '1px solid var(--border-color)';
            div.style.display = 'flex';
            div.style.justifyContent = 'space-between';
            div.style.alignItems = 'center';
            div.innerHTML = `
                <span>${wf.name}</span>
                <button class="secondary" style="padding:2px 8px; font-size:0.8em;" onclick="ghTriggerRun(${wf.id})">Run ▷</button>
            `;
            el.appendChild(div);
        });
    } catch(e) { el.innerHTML = `Error: ${e.message}`; }
}

async function loadGhRuns() {
    const el = document.getElementById('gh-runs-list');
    el.innerHTML = 'Loading...';
    try {
        const res = await fetch('/api/apps/github/actions/runs', {
            method:'POST',headers:{'Content-Type':'application/json'},
            body:JSON.stringify({repo:ghActionsRepo, account_id:ghActiveAccount.id})
        });
        const data = await res.json();
        if(data.error) throw new Error(data.error);

        el.innerHTML = '';
        data.forEach(run => {
            const div = document.createElement('div');
            div.className = 'gh-result-item'; // Reuse style

            let statusColor = '#c0caf5';
            if(run.status === 'completed') {
                statusColor = run.conclusion === 'success' ? 'var(--success-color)' : 'var(--error-color)';
            } else {
                statusColor = 'var(--warning-color)'; // In progress/Queued
            }

            div.innerHTML = `
                <div>
                    <div style="font-weight:bold; color:${statusColor};">${run.name} #${run.run_number}</div>
                    <div style="font-size:0.8em; color:var(--text-muted);">${run.status} (${run.conclusion || 'running'}) • ${run.event}</div>
                </div>
                ${run.status !== 'completed' ? `<button class="danger" style="padding:4px 8px; font-size:0.8em;" onclick="ghCancelRun(${run.id})">Stop</button>` : ''}
            `;
            el.appendChild(div);
        });
    } catch(e) { el.innerHTML = `Error: ${e.message}`; }
}

async function ghTriggerRun(id) {
    if(!confirm("Run this workflow on 'main'?")) return;
    await fetch('/api/apps/github/actions/run', {
        method:'POST',headers:{'Content-Type':'application/json'},
        body:JSON.stringify({repo:ghActionsRepo, id:id, account_id:ghActiveAccount.id})
    });
    showToast('Workflow Triggered', 'success');
    setTimeout(loadGhRuns, 2000);
}

async function ghCancelRun(id) {
    if(!confirm("Cancel this run?")) return;
    await fetch('/api/apps/github/actions/cancel', {
        method:'POST',headers:{'Content-Type':'application/json'},
        body:JSON.stringify({repo:ghActionsRepo, id:id, account_id:ghActiveAccount.id})
    });
    showToast('Cancellation Sent', 'success');
    setTimeout(loadGhRuns, 2000);
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
