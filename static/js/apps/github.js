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

// --- Browser Logic ---
let ghBrowserState = {
    owner: '',
    repo: '',
    path: '',
    branch: 'main'
};

function openGhBrowser(repoName) {
    const [owner, repo] = repoName.split('/');
    ghBrowserState = { owner, repo, path: '', branch: 'main' };

    document.getElementById('gh-browser-modal').style.display = 'flex';
    document.getElementById('gh-browser-title').innerText = `${repoName}`;

    loadGhBranches(owner, repo);
    loadGhContents();
}

async function loadGhBranches(owner, repo) {
    const select = document.getElementById('gh-browser-branch');
    select.innerHTML = '<option>Loading...</option>';
    select.disabled = true;

    try {
        const res = await fetch('/api/apps/github/repo/branches', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({owner, repo, account_id: ghActiveAccount.id})
        });
        const branches = await res.json();

        select.innerHTML = '';
        branches.forEach(b => {
            const opt = document.createElement('option');
            opt.value = b;
            opt.innerText = b;
            if(b === 'main' || b === 'master') opt.selected = true;
            select.appendChild(opt);
        });

        ghBrowserState.branch = select.value;
        select.disabled = false;
        select.onchange = () => {
            ghBrowserState.branch = select.value;
            loadGhContents();
        };
    } catch(e) {
        select.innerHTML = '<option>Error</option>';
    }
}

async function loadGhContents() {
    const list = document.getElementById('gh-browser-list');
    const crumbs = document.getElementById('gh-browser-breadcrumbs');

    list.innerHTML = 'Loading...';

    // Update breadcrumbs
    const parts = ghBrowserState.path.split('/').filter(p => p);
    let html = `<span style="cursor:pointer; color:var(--accent-color);" onclick="ghNavigate('')">ROOT</span>`;
    let current = '';
    parts.forEach((p, i) => {
        current += (i > 0 ? '/' : '') + p;
        const target = current; // capture for closure
        html += ` / <span style="cursor:pointer; color:var(--accent-color);" onclick="ghNavigate('${target}')">${p}</span>`;
    });
    crumbs.innerHTML = html;

    try {
        const res = await fetch('/api/apps/github/repo/contents', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                owner: ghBrowserState.owner,
                repo: ghBrowserState.repo,
                path: ghBrowserState.path,
                branch: ghBrowserState.branch,
                account_id: ghActiveAccount.id
            })
        });
        const data = await res.json();

        if(data.error) throw new Error(data.error);

        list.innerHTML = '';

        // Go Back Item
        if(ghBrowserState.path) {
            const parent = ghBrowserState.path.substring(0, ghBrowserState.path.lastIndexOf('/'));
            const row = document.createElement('div');
            row.className = 'gh-browser-item';
            row.style.padding = '10px';
            row.style.borderBottom = '1px solid var(--border-color)';
            row.style.cursor = 'pointer';
            row.innerHTML = `📁 ..`;
            row.onclick = () => ghNavigate(parent);
            list.appendChild(row);
        }

        if(data.type === 'file') {
            // Should not happen usually as we click to open
            openGhEditor(data);
            return;
        }

        if(data.items.length === 0) {
            list.innerHTML = '<div style="padding:20px; text-align:center; color:var(--text-muted);">Empty Directory</div>';
            return;
        }

        data.items.forEach(item => {
            const row = document.createElement('div');
            row.className = 'gh-browser-item';
            row.style.padding = '10px';
            row.style.borderBottom = '1px solid var(--border-color)';
            row.style.cursor = 'pointer';
            row.style.display = 'flex';
            row.style.justifyContent = 'space-between';
            row.style.alignItems = 'center';

            const icon = item.type === 'dir' ? '📁' : '📄';
            const color = item.type === 'dir' ? 'var(--accent-color)' : '#c0caf5';

            row.innerHTML = `
                <div style="display:flex; align-items:center; gap:10px;">
                    <span>${icon}</span>
                    <span style="color:${color};">${item.name}</span>
                </div>
                <div style="font-size:0.8em; color:var(--text-muted); display:flex; gap:10px; align-items:center;">
                    <span>${item.size ? formatBytes(item.size) : ''}</span>
                    <button class="danger icon-btn" onclick="deleteGhFile(event, '${item.path}', '${item.sha}')">🗑️</button>
                </div>
            `;

            row.onclick = (e) => {
                // Ignore button clicks
                if(e.target.tagName === 'BUTTON') return;

                if(item.type === 'dir') {
                    ghNavigate(item.path);
                } else {
                    // Fetch file details (content)
                    openGhFile(item.path);
                }
            };

            list.appendChild(row);
        });

    } catch(e) {
        list.innerHTML = `<div style="color:var(--error-color);">Error: ${e.message}</div>`;
    }
}

function ghNavigate(path) {
    ghBrowserState.path = path;
    loadGhContents();
}

async function deleteGhFile(e, path, sha) {
    e.stopPropagation();
    if(!confirm(`Delete ${path}?`)) return;

    try {
        const res = await fetch('/api/apps/github/repo/file/delete', {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                owner: ghBrowserState.owner,
                repo: ghBrowserState.repo,
                path: path,
                sha: sha,
                message: `Delete ${path}`,
                branch: ghBrowserState.branch,
                account_id: ghActiveAccount.id
            })
        });
        const data = await res.json();
        if(data.error) throw new Error(data.error);

        showToast('File Deleted', 'success');
        loadGhContents();
    } catch(e) {
        showToast(e.message, 'error');
    }
}

// --- Editor Logic ---
let ghEditorState = {
    path: '',
    sha: null
};

async function openGhFile(path) {
    // Check size first? We do it in loadContents logic usually, but here we just fetch
    // If it's huge, backend might choke or API limit.
    // We already have size in listing, but let's just try fetching.

    showToast('Opening file...', 'info');

    try {
        const res = await fetch('/api/apps/github/repo/contents', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                owner: ghBrowserState.owner,
                repo: ghBrowserState.repo,
                path: path,
                branch: ghBrowserState.branch,
                account_id: ghActiveAccount.id
            })
        });
        const data = await res.json();

        if(data.error) throw new Error(data.error);
        if(data.size > 1000000) { // 1MB Safety Limit
            alert(`File is too large (${formatBytes(data.size)}) to edit in browser.`);
            return;
        }

        ghEditorState = { path: data.path, sha: data.sha };

        document.getElementById('gh-editor-modal').style.display = 'flex';
        document.getElementById('gh-editor-filename').innerText = data.path;

        const content = atob(data.content); // Decode Base64
        document.getElementById('gh-editor-content').value = content;
        document.getElementById('gh-editor-message').value = ''; // Reset message

    } catch(e) {
        showToast(e.message, 'error');
    }
}

async function saveGhFile() {
    const content = document.getElementById('gh-editor-content').value;
    const message = document.getElementById('gh-editor-message').value || `Update ${ghEditorState.path}`;
    const contentB64 = btoa(content);

    try {
        const res = await fetch('/api/apps/github/repo/file/put', {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                owner: ghBrowserState.owner,
                repo: ghBrowserState.repo,
                path: ghEditorState.path,
                content: contentB64,
                message: message,
                sha: ghEditorState.sha,
                branch: ghBrowserState.branch,
                account_id: ghActiveAccount.id
            })
        });
        const data = await res.json();
        if(data.error) throw new Error(data.error);

        showToast('File Saved', 'success');
        document.getElementById('gh-editor-modal').style.display = 'none';
        loadGhContents(); // Refresh list
    } catch(e) {
        showToast(e.message, 'error');
    }
}

// --- Upload Logic ---

function openGhUploadModal() {
    document.getElementById('gh-upload-modal').style.display = 'block';
}

function handleGhPcUpload(input) {
    const file = input.files[0];
    if(!file) return;

    const reader = new FileReader();
    reader.onload = async function(e) {
        const contentB64 = e.target.result.split(',')[1]; // Remove data URL prefix
        const path = ghBrowserState.path ? `${ghBrowserState.path}/${file.name}` : file.name;

        showToast('Uploading...', 'info');

        try {
            const res = await fetch('/api/apps/github/repo/file/put', {
                method: 'POST', headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    owner: ghBrowserState.owner,
                    repo: ghBrowserState.repo,
                    path: path,
                    content: contentB64,
                    message: `Upload ${file.name}`,
                    branch: ghBrowserState.branch,
                    account_id: ghActiveAccount.id
                })
            });
            const data = await res.json();
            if(data.error) throw new Error(data.error);

            showToast('Upload Successful', 'success');
            document.getElementById('gh-upload-modal').style.display = 'none';
            loadGhContents();
        } catch(err) {
            showToast(err.message, 'error');
        }
    };
    reader.readAsDataURL(file);
}

function openGhServerPicker() {
    document.getElementById('gh-upload-modal').style.display = 'none';
    // Reuse Move/Copy Modal but hijack its Confirm action?
    // Or build a custom picker. Let's hijack the MC modal for simplicity if possible,
    // but the MC modal is wired to specific buttons.
    // Better: Open MC modal with a special "mode".

    // We can simulate clicking "Copy" but that's messy.
    // Let's create a minimal picker or reuse the logic.
    // I'll reuse the `openMcModal` but pass a callback context? No, `openMcModal` is in main.js/files.js
    // I will call `openMcModal('gh-upload')`.
    // I need to modify `files.js` or `main.js` to handle this 'gh-upload' mode or just add a listener.
    // WAIT: `openMcModal` is designed for Destination selection (Folders).
    // For Upload from Server, we want to select a SOURCE FILE.
    // The main file browser is for source selection.

    // Alternative:
    // Ask user to "Select a file in the Files tab first".
    // Just like the Publisher.

    if(selectedPaths.length === 1 && browserMode === 'local') {
        // We have a file selected
        startGhServerUpload(selectedPaths[0]);
    } else {
        alert("Please go to the 'Files' tab, select ONE local file, then come back here.");
    }
}

async function startGhServerUpload(localPath) {
    const filename = localPath.split('/').pop();
    const remotePath = ghBrowserState.path ? `${ghBrowserState.path}/${filename}` : filename;

    if(!confirm(`Upload '${filename}' to GitHub folder '${ghBrowserState.path || 'root'}'?`)) return;

    try {
        const res = await fetch('/api/apps/github/repo/upload-server', {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                owner: ghBrowserState.owner,
                repo: ghBrowserState.repo,
                local_path: localPath,
                remote_path: remotePath,
                message: `Upload ${filename} from server`,
                branch: ghBrowserState.branch,
                account_id: ghActiveAccount.id
            })
        });
        const data = await res.json();
        if(data.error) throw new Error(data.error);

        showToast('Server Upload Queued', 'success');
        document.getElementById('gh-upload-modal').style.display = 'none';
        // Note: It's async, so list won't update immediately.
    } catch(e) {
        showToast(e.message, 'error');
    }
}

// --- New Folder Logic ---
function openGhNewFolderModal() {
    const name = prompt("New Folder Name:");
    if(!name) return;

    // Create .gitkeep
    const path = ghBrowserState.path ? `${ghBrowserState.path}/${name}/.gitkeep` : `${name}/.gitkeep`;

    // We reuse create file logic
    // Content empty base64 = ""
    fetch('/api/apps/github/repo/file/put', {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            owner: ghBrowserState.owner,
            repo: ghBrowserState.repo,
            path: path,
            content: "", // Empty file
            message: `Create folder ${name}`,
            branch: ghBrowserState.branch,
            account_id: ghActiveAccount.id
        })
    }).then(r=>r.json()).then(data => {
        if(data.error) showToast(data.error, 'error');
        else {
            showToast('Folder Created', 'success');
            loadGhContents();
        }
    });
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
    // Repo Search Filter
    const repoFilter = document.getElementById('gh-repos-filter');
    if(repoFilter) {
        repoFilter.oninput = (e) => filterMyRepos(e.target.value);
    }

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
            card.className = 'app-card gh-repo-card'; // Hook for search
            card.dataset.name = repo.name.toLowerCase(); // Search data
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
                    <button class="info-btn" style="flex:0; font-size:0.8em; padding:6px; background:var(--accent-color); color:#000;" onclick="openGhBrowser('${repo.name}')" title="Browse Code">📂</button>
                    <button class="info-btn" style="flex:0; font-size:0.8em; padding:6px;" onclick="ghOpenSecrets('${repo.name}')" title="Secrets">🔑</button>
                    <button class="info-btn" style="flex:0; font-size:0.8em; padding:6px;" onclick="ghOpenActions('${repo.name}')" title="Actions">▶</button>
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

function filterMyRepos(query) {
    const q = query.toLowerCase().trim();
    document.querySelectorAll('.gh-repo-card').forEach(card => {
        const name = card.dataset.name || '';
        if(name.includes(q)) card.style.display = 'flex';
        else card.style.display = 'none';
    });
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
            <div style="display:flex; gap:15px; align-items:center; flex:1;">
                <div>Found ${data.length} Releases</div>
                <input type="text" id="gh-release-filter" placeholder="🔍 Filter versions or files..."
                       style="background:#13141c; border:1px solid var(--border-color); color:var(--text-color); padding:5px 10px; border-radius:4px; font-size:0.9em; flex:1; max-width:300px;">
            </div>
            <button class="purple-btn" style="padding:5px 10px; font-size:0.8em;" onclick="triggerGhClone('${repo}')">Clone Source</button>
        `;

        // Wire Filter Logic
        document.getElementById('gh-release-filter').oninput = (e) => filterGhReleases(e.target.value);

        ghResults.innerHTML = '';
        if(!data || data.length === 0) {
            ghResults.innerHTML = '<div style="padding:10px;">No releases found.</div>';
            return;
        }

        // Render Release Cards
        data.forEach((release, index) => {
            const releaseCard = document.createElement('div');
            releaseCard.className = 'gh-release-card'; // Hook for filter
            releaseCard.style.background = 'var(--panel-bg)';
            releaseCard.style.border = '1px solid var(--border-color)';
            releaseCard.style.marginBottom = '10px';
            releaseCard.style.borderRadius = '6px';
            releaseCard.style.overflow = 'hidden';

            const isLatest = index === 0;
            const badge = isLatest ? '<span style="background:var(--success-color); color:#000; padding:2px 6px; border-radius:4px; font-size:0.7em; margin-left:8px; font-weight:bold;">LATEST</span>' : '';
            const preBadge = release.prerelease ? '<span style="background:var(--warning-color); color:#000; padding:2px 6px; border-radius:4px; font-size:0.7em; margin-left:8px; font-weight:bold;">PRE</span>' : '';
            const dateStr = new Date(release.published_at).toLocaleDateString();

            // Store data for search
            releaseCard.dataset.tag = (release.tag || '').toLowerCase();
            releaseCard.dataset.name = (release.name||'').toLowerCase();

            // Card Header (Clickable)
            const headerDiv = document.createElement('div');
            headerDiv.style.padding = '12px 15px';
            headerDiv.style.cursor = 'pointer';
            headerDiv.style.display = 'flex';
            headerDiv.style.justifyContent = 'space-between';
            headerDiv.style.alignItems = 'center';
            headerDiv.style.background = 'rgba(255,255,255,0.02)';

            // Generate Download All Button (Only if assets exist)
            const hasAssets = release.assets && release.assets.length > 0;

            // Buttons
            const dlAllBtn = hasAssets ? `<button class="purple-btn gh-btn-action" data-action="dl-all" style="padding:2px 8px; font-size:0.7em; margin-left:10px;">Download All</button>` : '';
            const delAllBtn = hasAssets ? `<button class="danger gh-btn-action" data-action="del-all" style="padding:2px 8px; font-size:0.7em; margin-left:5px; background:none; border:1px solid var(--error-color); color:var(--error-color);">Trash All</button>` : '';
            const delRelBtn = `<button class="danger gh-btn-action" data-action="del-rel" style="padding:2px 8px; font-size:0.7em; margin-left:5px; background:none; border:1px solid var(--error-color); color:var(--error-color);">Del Release</button>`;

            headerDiv.innerHTML = `
                <div style="display:flex; align-items:center;">
                    <div style="font-weight:bold; color:#c0caf5; font-size:1.1em;" class="gh-tag-text">${release.tag}</div>
                    ${badge}
                    ${preBadge}
                    ${dlAllBtn}
                    ${delAllBtn}
                    ${delRelBtn}
                </div>
                <div style="font-size:0.8em; color:var(--text-muted); display:flex; align-items:center; gap:10px;">
                    <span>${dateStr}</span>
                    <span style="transform: rotate(${isLatest?0:-90}deg); transition: transform 0.2s;" class="arrow-icon">▼</span>
                </div>
            `;

            // Wire Header Buttons
            headerDiv.querySelectorAll('.gh-btn-action').forEach(btn => {
                btn.onclick = (e) => {
                    e.stopPropagation();
                    const action = btn.dataset.action;
                    if(action === 'dl-all') {
                        const assetPayload = release.assets.map(a => ({url: a.download_url, filename: a.name}));
                        downloadGhBatch(assetPayload, release.tag);
                    } else if(action === 'del-all') {
                        deleteGhAssets(release.assets, repo);
                    } else if(action === 'del-rel') {
                        deleteGhRelease(release.id, repo);
                    }
                };
            });

            // Assets Container
            const assetsDiv = document.createElement('div');
            assetsDiv.className = 'gh-assets-container';
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
                    row.className = 'gh-result-item gh-asset-row'; // Reuse style + hook
                    row.dataset.filename = asset.name.toLowerCase();
                    row.style.marginBottom = '5px';
                    row.innerHTML = `
                        <div style="display:flex; align-items:center; gap:10px;">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="color:#565f89"><path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"></path><polyline points="13 2 13 9 20 9"></polyline></svg>
                            <div>
                                <div style="color:#a9b1d6; font-size:0.95em;">${asset.name}</div>
                                <div style="font-size:0.75em; color:var(--text-muted);">${formatBytes(asset.size)}</div>
                            </div>
                        </div>
                        <div style="display:flex; gap:5px;">
                            <button class="icon-btn dl-btn" style="color:var(--success-color); border:1px solid #2f3549; padding:4px 8px; border-radius:4px;" title="Download">⬇️</button>
                            <button class="icon-btn del-btn" style="color:var(--error-color); border:1px solid #2f3549; padding:4px 8px; border-radius:4px;" title="Delete">🗑️</button>
                        </div>
                    `;
                    row.querySelector('.dl-btn').onclick = (e) => {
                         e.stopPropagation();
                         downloadGhAsset(asset.download_url, asset.name);
                    };
                    row.querySelector('.del-btn').onclick = (e) => {
                         e.stopPropagation();
                         deleteGhAsset(asset.id, asset.name, repo);
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

function filterGhReleases(query) {
    const q = query.toLowerCase().trim();
    const cards = document.querySelectorAll('.gh-release-card');

    cards.forEach(card => {
        const tag = card.dataset.tag || '';
        const name = card.dataset.name || '';
        const header = card.querySelector('.gh-tag-text');

        let matchRelease = tag.includes(q) || name.includes(q);
        let matchAsset = false;

        const assetRows = card.querySelectorAll('.gh-asset-row');
        assetRows.forEach(row => {
            const filename = row.dataset.filename || '';
            if (filename.includes(q)) {
                matchAsset = true;
                row.style.display = 'flex'; // Show asset
                // Highlight logic could go here
                row.style.background = q ? 'rgba(187, 154, 247, 0.1)' : 'none';
            } else {
                row.style.display = q ? 'none' : 'flex';
            }
        });

        if (q === '') {
            // Reset visibility
            card.style.display = 'block';
            assetRows.forEach(r => { r.style.display = 'flex'; r.style.background = 'none'; });
            // Don't auto-close, leave as is or reset? Let's leave as is for UX.
            return;
        }

        if (matchRelease || matchAsset) {
            card.style.display = 'block';
            if (matchAsset) {
                // Expand if asset matched
                const assetsDiv = card.querySelector('.gh-assets-container');
                const arrow = card.querySelector('.arrow-icon');
                if (assetsDiv) assetsDiv.style.display = 'block';
                if (arrow) arrow.style.transform = 'rotate(-90deg)';
            }
        } else {
            card.style.display = 'none';
        }
    });
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

// --- Secrets Logic ---
let ghSecretsRepo = '';

async function ghOpenSecrets(repo) {
    ghSecretsRepo = repo;
    document.getElementById('gh-secrets-title').textContent = `Secrets: ${repo}`;
    document.getElementById('gh-secrets-modal').style.display = 'block';
    document.getElementById('gh-secret-name').value = '';
    document.getElementById('gh-secret-value').value = '';
    loadGhSecrets();
}

async function loadGhSecrets() {
    const el = document.getElementById('gh-secrets-list');
    el.innerHTML = 'Loading...';

    const [owner, repo] = ghSecretsRepo.split('/');
    try {
        const res = await fetch('/api/apps/github/secrets/list', {
            method:'POST', headers:{'Content-Type':'application/json'},
            body:JSON.stringify({owner, repo, account_id:ghActiveAccount.id})
        });
        const data = await res.json();
        if(data.error) throw new Error(data.error);

        el.innerHTML = '';
        if(data.secrets.length === 0) {
            el.innerHTML = '<div style="color:var(--text-muted);">No secrets found.</div>';
            return;
        }

        data.secrets.forEach(s => {
            const div = document.createElement('div');
            div.style.display='flex'; div.style.justifyContent='space-between'; div.style.padding='8px';
            div.style.borderBottom='1px solid var(--border-color)';
            div.innerHTML = `
                <span style="font-family:monospace; color:#e0af68;">${s.name}</span>
                <div style="font-size:0.8em; color:var(--text-muted);">Updated ${new Date(s.updated_at).toLocaleDateString()}</div>
                <button class="icon-btn" style="color:var(--error-color);" onclick="deleteGhSecret('${s.name}')">🗑️</button>
            `;
            el.appendChild(div);
        });
    } catch(e) { el.innerHTML = `Error: ${e.message}`; }
}

async function saveGhSecret() {
    const name = document.getElementById('gh-secret-name').value;
    const value = document.getElementById('gh-secret-value').value;
    if(!name || !value) return showToast('Name and Value required', 'error');

    const [owner, repo] = ghSecretsRepo.split('/');
    try {
        const res = await fetch('/api/apps/github/secrets/put', {
            method:'POST', headers:{'Content-Type':'application/json'},
            body:JSON.stringify({owner, repo, name, value, account_id:ghActiveAccount.id})
        });
        const data = await res.json();
        if(data.error) throw new Error(data.error);

        showToast('Secret Saved', 'success');
        document.getElementById('gh-secret-name').value = '';
        document.getElementById('gh-secret-value').value = '';
        loadGhSecrets();
    } catch(e) { showToast(e.message, 'error'); }
}

async function deleteGhSecret(name) {
    if(!confirm(`Delete secret ${name}?`)) return;
    const [owner, repo] = ghSecretsRepo.split('/');
    try {
        const res = await fetch('/api/apps/github/secrets/delete', {
            method:'POST', headers:{'Content-Type':'application/json'},
            body:JSON.stringify({owner, repo, name, account_id:ghActiveAccount.id})
        });
        const data = await res.json();
        if(data.error) throw new Error(data.error);
        showToast('Secret Deleted', 'success');
        loadGhSecrets();
    } catch(e) { showToast(e.message, 'error'); }
}

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

async function downloadGhBatch(assets, releaseTag) {
    const sub = prompt(`Batch Download (${assets.length} items) for ${releaseTag} to folder:`, `Downloads/${releaseTag}/`);
    if(sub === null) return;

    const body = { assets, path: sub };
    if(ghActiveAccount) body.account_id = ghActiveAccount.id;

    await fetch('/api/apps/github/download/batch', {
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify(body)
    });
    showToast('Batch Download Queued', 'success');
}

async function deleteGhRelease(id, repoFullName) {
    if(!confirm('⚠️ Are you sure you want to DELETE this release?')) return;
    const [owner, repo] = repoFullName.split('/');

    try {
        const res = await fetch('/api/apps/github/release/delete', {
            method:'POST', headers:{'Content-Type':'application/json'},
            body:JSON.stringify({owner, repo, release_id:id, account_id:ghActiveAccount.id})
        });
        const data = await res.json();
        if(data.error) throw new Error(data.error);
        showToast('Release Deleted', 'success');
        fetchGhReleases(ghCurrentPage);
    } catch(e) { showToast(e.message, 'error'); }
}

async function deleteGhAsset(id, name, repoFullName) {
    if(!confirm(`Delete asset '${name}'?`)) return;
    const [owner, repo] = repoFullName.split('/');

    try {
        const res = await fetch('/api/apps/github/release/asset/delete', {
            method:'POST', headers:{'Content-Type':'application/json'},
            body:JSON.stringify({owner, repo, asset_id:id, account_id:ghActiveAccount.id})
        });
        const data = await res.json();
        if(data.error) throw new Error(data.error);
        showToast('Asset Deleted', 'success');
        fetchGhReleases(ghCurrentPage);
    } catch(e) { showToast(e.message, 'error'); }
}

async function deleteGhAssets(assets, repoFullName) {
    if(!confirm(`Delete ALL ${assets.length} assets from this release?`)) return;
    // Sequential deletion or batch endpoint?
    // User requested "delete all assets", we don't have a batch API for deletion yet in backend plan.
    // I will loop here for now, or add batch endpoint.
    // Adding loop here is safer for immediate feedback.

    const [owner, repo] = repoFullName.split('/');
    let count = 0;

    for(const asset of assets) {
        try {
            await fetch('/api/apps/github/release/asset/delete', {
                method:'POST', headers:{'Content-Type':'application/json'},
                body:JSON.stringify({owner, repo, asset_id:asset.id, account_id:ghActiveAccount.id})
            });
            count++;
        } catch(e) {}
    }
    showToast(`Deleted ${count} assets`, 'success');
    fetchGhReleases(ghCurrentPage);
}

// Publisher
let ghPubCurrentPage = 1;

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

async function fetchGhPubReleases(page=1) {
    const repo = document.getElementById('gh-pub-repo-fetch').value;
    const container = document.getElementById('gh-pub-fetch-container');
    const results = document.getElementById('gh-pub-results');

    if(!repo) return showToast('Enter Repo to fetch', 'error');
    ghPubCurrentPage = page;

    container.style.display = 'block';
    results.innerHTML = `<div style="padding:10px; color:var(--text-muted);">Fetching page ${page}...</div>`;

    try {
        const body = { repo, page };
        if(ghActiveAccount) body.account_id = ghActiveAccount.id;

        const res = await fetch('/api/apps/github/releases', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
        const data = await res.json();

        if(data.error) throw new Error(data.error);

        results.innerHTML = '';
        if(!data || data.length === 0) {
            results.innerHTML = '<div style="padding:10px;">No releases found.</div>';
            return;
        }

        // Render compact list for selection
        data.forEach(rel => {
            const row = document.createElement('div');
            row.className = 'gh-pub-release-row'; // Hook for search
            row.dataset.tag = (rel.tag || '').toLowerCase();
            row.style.padding = '8px';
            row.style.borderBottom = '1px solid var(--border-color)';
            row.style.display = 'flex';
            row.style.justifyContent = 'space-between';
            row.style.alignItems = 'center';

            row.innerHTML = `
                <div>
                    <span style="font-weight:bold; color:#c0caf5;">${rel.tag}</span>
                    <span style="font-size:0.8em; color:var(--text-muted); margin-left:10px;">${new Date(rel.published_at).toLocaleDateString()}</span>
                </div>
                <button class="secondary" style="padding:2px 8px; font-size:0.7em;">Select</button>
            `;

            row.querySelector('button').onclick = () => {
                document.getElementById('gh-pub-tag').value = rel.tag;
                document.getElementById('gh-pub-repo').value = repo; // Auto-fill target repo same as source
                // Update Button Text to indicate mode change
                const pubBtn = document.querySelector('#gh-view-pub button[onclick="triggerGhPublish()"]');
                if(pubBtn) {
                    pubBtn.innerText = 'Upload to Existing Release';
                    pubBtn.classList.remove('secondary');
                    pubBtn.classList.add('purple-btn');
                }
                showToast(`Selected ${rel.tag}`, 'success');
            };
            results.appendChild(row);
        });

        // Pagination for Publisher
        const nav = document.createElement('div');
        nav.style.display = 'flex';
        nav.style.justifyContent = 'center';
        nav.style.gap = '10px';
        nav.style.padding = '5px';
        nav.style.background = '#15161e';

        if (page > 1) {
            const prev = document.createElement('button');
            prev.className = 'secondary';
            prev.innerText = '⬅️';
            prev.onclick = () => fetchGhPubReleases(page - 1);
            nav.appendChild(prev);
        }
        if (data.length === 30) {
            const next = document.createElement('button');
            next.className = 'secondary';
            next.innerText = '➡️';
            next.onclick = () => fetchGhPubReleases(page + 1);
            nav.appendChild(next);
        }
        if(nav.children.length > 0) results.appendChild(nav);

        // Search Filter Logic for Publisher
        const filterInput = document.getElementById('gh-pub-filter');
        filterInput.oninput = (e) => {
            const q = e.target.value.toLowerCase();
            document.querySelectorAll('.gh-pub-release-row').forEach(r => {
                const t = r.dataset.tag;
                r.style.display = t.includes(q) ? 'flex' : 'none';
            });
        };

    } catch(e) {
        results.innerHTML = `<div style="color:var(--error-color); padding:10px;">Error: ${e.message}</div>`;
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
