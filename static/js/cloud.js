// --- Cloud / Rclone Logic ---

async function loadRemotesList() {
    // Reset selection on nav
    selectedPaths = [];
    document.getElementById('select-all-check').checked = false;
    updateButtonState();

    const fileList = document.getElementById('file-list');
    const breadcrumb = document.getElementById('current-path');

    try {
        fileList.innerHTML = '<div style="padding:20px;text-align:center;">Loading Remotes...</div>';
        const res = await fetch('/api/remotes');
        const remotes = await res.json();

        currentPath = ''; currentRemote = '';
        breadcrumb.innerHTML = '<span style="color:var(--accent-color);">Cloud Remotes</span>';

        fileList.innerHTML = '';
        remotes.forEach(r => {
            const li = document.createElement('li');
            li.className = 'file-item';
            li.innerHTML = `<span class="icon" style="color:#bb9af7">☁️</span> ${r}`;
            li.onclick = () => loadCloudPath('', r);
            fileList.appendChild(li);
        });
        updateButtonState();
    } catch(e) { showToast('Error loading remotes', 'error'); }
}

async function loadCloudPath(path, remoteOverride=null) {
    // Reset selection on nav
    selectedPaths = [];
    document.getElementById('select-all-check').checked = false;
    updateButtonState();

    if(remoteOverride) currentRemote = remoteOverride;
    if(!currentRemote) { loadRemotesList(); return; }

    const fileList = document.getElementById('file-list');
    const breadcrumb = document.getElementById('current-path');

    try {
        fileList.innerHTML = '<div style="padding:20px;text-align:center;">Loading Cloud...</div>';
        const res = await fetch(`/api/rclone/list?remote=${encodeURIComponent(currentRemote)}&path=${encodeURIComponent(path)}`);
        const data = await res.json();
        if(data.error) throw new Error(data.error);

        currentPath = data.current_path;
        renderBreadcrumb(currentPath, 'cloud');

        fileList.innerHTML = '';
        if(currentPath==='') {
            const li = document.createElement('li'); li.className='file-item';
            li.innerHTML = '<span class="icon dir-icon">📁</span> .. (Remotes)';
            li.onclick = () => loadRemotesList();
            fileList.appendChild(li);
        } else if(data.parent_path !== null) {
            const li = document.createElement('li'); li.className='file-item';
            li.innerHTML = '<span class="icon dir-icon">📁</span> ..';
            li.onclick = () => loadCloudPath(data.parent_path);
            fileList.appendChild(li);
        }

        updateButtonState();

        data.items.forEach(item => {
            const li = document.createElement('li');
            li.className = 'file-item';

            const cb = document.createElement('input'); cb.type='checkbox';
            cb.dataset.path = item.path;
            cb.onclick = (e) => { e.stopPropagation(); toggleSelection(item.path, cb.checked); };

            let icon = item.is_dir ? '📁' : '📄';
            let cls = item.is_dir ? 'dir-icon' : 'file-icon';
            if(!item.is_dir && /\.(mkv|mp4|avi)$/i.test(item.name)) icon = '🎬';
            if(!item.is_dir && item.name.endsWith('.par2')) { icon='🔧'; cls='par2-icon'; }

            li.innerHTML = `<span class="${cls} icon">${icon}</span> <span>${item.name}</span>`;
            li.prepend(cb);

            if(item.size) {
                const sz = document.createElement('span');
                sz.style.marginLeft='auto'; sz.style.fontSize='0.8em'; sz.style.color='var(--text-muted)';
                sz.textContent = formatBytes(item.size);
                li.appendChild(sz);
            }

            if(item.is_dir) li.onclick = (e) => { if(e.target!==cb) loadCloudPath(item.path); };

            fileList.appendChild(li);
        });
    } catch(e) { showToast(e.message, 'error'); }
}

// --- Move/Copy Browser Logic ---
function openMcModal(action) {
    mcAction=action;
    mcContext = (browserMode==='cloud' && action!=='download') ? 'cloud' : 'local';
    document.getElementById('mc-title').textContent = `${action.toUpperCase()} to ${mcContext.toUpperCase()}`;
    loadMcBrowser('');
    document.getElementById('move-copy-modal').style.display='block';
}

async function loadMcBrowser(path) {
    mcCurrentBrowserPath = path;
    const disp = document.getElementById('mc-selected-path');
    const cont = document.getElementById('mc-browser');

    disp.textContent = path || '/';
    cont.innerHTML = 'Loading...';

    try {
        let items = [];
        if(mcContext==='cloud') {
             if(!path) {
                 const r = await(await fetch('/api/remotes')).json();
                 items = r.map(x=>({name:x, is_dir:true, fullPath:x, is_remote:true}));
             } else {
                 let remote=path, sub='';
                 if(path.includes('/')) { remote=path.split('/')[0]; sub=path.substring(path.indexOf('/')+1); }
                 const res = await(await fetch(`/api/rclone/list?remote=${remote}&path=${sub}`)).json();
                 items = res.items.filter(i=>i.is_dir).map(i=>({name:i.name, is_dir:true, fullPath:remote+'/'+i.path}));
             }
        } else {
            const res = await(await fetch(`/api/list?path=${path}`)).json();
            items = res.items.filter(i=>i.is_dir).map(i=>({name:i.name, is_dir:true, fullPath:i.path}));
        }

        cont.innerHTML = '';
        const ul = document.createElement('ul'); ul.style.listStyle='none'; ul.style.padding=0;
        items.forEach(i => {
            const li = document.createElement('li'); li.style.padding='5px'; li.style.cursor='pointer';
            li.innerHTML = (i.is_remote?'☁️ ':'📁 ') + i.name;
            li.onclick = () => loadMcBrowser(i.fullPath);
            ul.appendChild(li);
        });
        cont.appendChild(ul);
    } catch(e) { cont.textContent = 'Error'; }
}

async function loadRemotesSelect(el) {
    el.innerHTML='';
    const r = await (await fetch('/api/remotes')).json();
    r.forEach(x => { const o=document.createElement('option'); o.value=x; o.textContent=x; el.appendChild(o); });
}

// --- Wire Cloud Events ---
document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('cloud-move-btn').onclick = () => openMcModal('move');
    document.getElementById('cloud-copy-btn').onclick = () => openMcModal('copy');
    document.getElementById('download-btn').onclick = () => openMcModal('download');

    document.getElementById('cloud-rename-btn').onclick = () => {
        document.getElementById('rename-input').value=selectedPaths[0].split('/').pop();
        document.getElementById('rename-modal').style.display='block';
    };

    document.getElementById('cloud-delete-btn').onclick = async () => {
         if(confirm('Delete Cloud Items?')) {
             await fetch('/api/rclone/delete', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({remote:currentRemote, paths:selectedPaths})});
             showToast('Delete Queued', 'success');
         }
    };

    // Mc Modal Events
    document.getElementById('mc-up-btn').onclick = () => {
         if(!mcCurrentBrowserPath) return;
         if(!mcCurrentBrowserPath.includes('/')) loadMcBrowser('');
         else loadMcBrowser(mcCurrentBrowserPath.substring(0, mcCurrentBrowserPath.lastIndexOf('/')));
    };

    document.getElementById('confirm-mc').onclick = async () => {
        document.getElementById('move-copy-modal').style.display='none';
        const dest = mcCurrentBrowserPath;

        // Logic for Cloud/Cross-Remote
        if(mcContext==='cloud') {
            let r=currentRemote, p=dest, dr=currentRemote; // defaults
            if(dest) {
                if(dest.includes('/')) { dr=dest.split('/')[0]; p=dest.substring(dest.indexOf('/')+1); }
                else { dr=dest; p=''; }
            }

            const ep = (mcAction==='move'?'/api/rclone/move':'/api/rclone/copy');
            await fetch(ep, {
                method:'POST',headers:{'Content-Type':'application/json'},
                body:JSON.stringify({remote:currentRemote, paths:selectedPaths, destination:p, dest_remote:dr})
            });
            showToast('Queued', 'success');
        } else if(mcAction==='download') {
             await fetch('/api/rclone/download', {
                 method:'POST',headers:{'Content-Type':'application/json'},
                 body:JSON.stringify({remote:currentRemote, paths:selectedPaths, destination:dest, transfers:4})
             });
             showToast('Download Queued', 'success');
        } else {
            // Local to Local
             const ep = (mcAction==='move'?'/api/move':'/api/copy');
             await fetch(ep, {
                 method:'POST',headers:{'Content-Type':'application/json'},
                 body:JSON.stringify({paths:selectedPaths, destination:dest})
             });
             showToast('Completed', 'success');
             if (typeof loadPath === 'function') loadPath(currentPath);
        }
    };
});
