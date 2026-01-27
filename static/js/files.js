async function loadLocalPath(path) {
    // Reset selection on nav
    selectedPaths = [];
    document.getElementById('select-all-check').checked = false;
    updateButtonState();

    const fileList = document.getElementById('file-list');
    const breadcrumb = document.getElementById('current-path');

    try {
        fileList.innerHTML = '<div style="padding:20px;text-align:center;color:var(--text-muted);">Loading...</div>';
        const res = await fetch(`/api/list?path=${encodeURIComponent(path)}`);
        const data = await res.json();
        if(data.error) throw new Error(data.error);

        currentPath = data.current_path;
        renderBreadcrumb(currentPath, 'local');
        renderFiles(data.items, data.parent_path);
    } catch(e) { showToast(e.message, 'error'); }
}

function loadPath(path) {
    if(browserMode==='local') loadLocalPath(path);
    else if (typeof loadCloudPath === 'function') loadCloudPath(path);
}

function switchBrowserMode(mode) {
    browserMode = mode;
    selectedPaths = [];
    document.getElementById('select-all-check').checked = false;

    const tabLocal = document.getElementById('tab-local');
    const tabCloud = document.getElementById('tab-cloud');
    const localControls = document.getElementById('local-controls');
    const cloudControls = document.getElementById('cloud-controls');

    if(mode === 'local') {
        tabLocal.classList.add('active');
        tabCloud.classList.remove('active');
        localControls.style.display = 'contents';
        cloudControls.style.display = 'none';
        loadPath('');
    } else {
        tabCloud.classList.add('active');
        tabLocal.classList.remove('active');
        localControls.style.display = 'none';
        cloudControls.style.display = 'block';
        if (typeof loadRemotesList === 'function') loadRemotesList();
    }
    updateButtonState();
}

function renderBreadcrumb(path, mode) {
    const breadcrumb = document.getElementById('current-path');
    breadcrumb.innerHTML = '';
    if(mode==='local') {
        breadcrumb.innerHTML = '<span onclick="loadPath(\'\')">ROOT</span> / ';
    } else {
        // Handled in Cloud JS usually, but fallback here
        breadcrumb.innerHTML = '<span onclick="loadRemotesList()">REMOTES</span> / ';
    }
    const parts = path.split('/').filter(Boolean);
    let acc = '';
    parts.forEach((p,i) => {
        acc += (acc?'/':'')+p;
        const sp = document.createElement('span');
        sp.textContent = p + (i<parts.length-1 ? ' / ' : '');
        const target = acc;
        sp.onclick = () => loadPath(target);
        breadcrumb.appendChild(sp);
    });
}

function renderFiles(items, parentPath) {
    const fileList = document.getElementById('file-list');
    fileList.innerHTML = '';
    if(parentPath!==null) {
        const li = document.createElement('li'); li.className='file-item';
        li.innerHTML = '<span class="icon dir-icon">📁</span> ..';
        li.onclick = () => loadPath(parentPath);
        fileList.appendChild(li);
    }
    items.forEach(item => {
        const li = document.createElement('li'); li.className='file-item';
        const cb = document.createElement('input'); cb.type='checkbox';
        cb.dataset.path = item.path;
        cb.onclick = (e) => { e.stopPropagation(); toggleSelection(item.path, cb.checked); };

        let icon = item.is_dir ? '📁' : '📄';
        let cls = item.is_dir ? 'dir-icon' : 'file-icon';
        if(!item.is_dir && item.name.endsWith('.par2')) { icon='🔧'; cls='par2-icon'; }

        // Media Viewer Click Handler for specific types
        const ext = item.name.split('.').pop().toLowerCase();
        const isImage = ['jpg','jpeg','png','gif','webp','svg','bmp','ico'].includes(ext);
        const isVideo = ['mp4','webm','mkv','mov'].includes(ext); // Browser supports mp4/webm mostly
        const isAudio = ['mp3','wav','ogg','flac','m4a'].includes(ext);

        let clickHandler = null;
        if(item.is_dir) {
            clickHandler = (e) => { if(e.target!==cb) loadPath(item.path); };
        } else if (browserMode === 'local' && (isImage || isVideo || isAudio)) {
            // Only local files can be served directly by the viewer route efficiently
            clickHandler = (e) => {
                if(e.target!==cb) {
                    e.preventDefault();
                    e.stopPropagation();
                    openMediaViewer(item.path, isImage ? 'image' : (isVideo ? 'video' : 'audio'));
                }
            };
        }

        li.innerHTML = `<span class="${cls} icon">${icon}</span> <span class="file-name">${item.name}</span>`;
        li.prepend(cb);

        if(clickHandler) li.onclick = clickHandler;

        // Add pointer cursor for clickable items
        if(item.is_dir || (browserMode === 'local' && (isImage || isVideo || isAudio))) {
            li.style.cursor = 'pointer';
        }

        fileList.appendChild(li);
    });
}

function openMediaViewer(path, type) {
    const modal = document.getElementById('media-viewer-modal');
    const content = document.getElementById('media-viewer-content');
    const title = document.getElementById('media-viewer-title');
    const src = `/api/files/serve?path=${encodeURIComponent(path)}`;

    title.textContent = path.split('/').pop();
    content.innerHTML = '';

    if (type === 'image') {
        content.innerHTML = `<img src="${src}" style="max-width:100%; max-height:85vh; border-radius:4px; box-shadow: 0 0 20px rgba(0,0,0,0.5);">`;
    } else if (type === 'video') {
        content.innerHTML = `<video controls autoplay style="max-width:100%; max-height:85vh; border-radius:4px;"><source src="${src}">Your browser does not support video.</video>`;
    } else if (type === 'audio') {
        content.innerHTML = `
            <div style="background:var(--panel-bg); padding:40px; border-radius:10px; display:flex; flex-direction:column; align-items:center; gap:20px;">
                <div style="font-size:3em;">🎵</div>
                <audio controls autoplay style="width:300px;"><source src="${src}">Your browser does not support audio.</audio>
            </div>
        `;
    }

    modal.style.display = 'flex';
}

function toggleSelection(path, checked) {
    if(checked) selectedPaths.push(path);
    else selectedPaths = selectedPaths.filter(p=>p!==path);
    updateButtonState();
}

function updateButtonState() {
    const has = selectedPaths.length > 0;
    const single = selectedPaths.length === 1;

    // Get Buttons
    const newFolderBtn = document.getElementById('new-folder-btn');
    const repairBtn = document.getElementById('repair-btn');
    const extractBtn = document.getElementById('extract-btn');
    const archiveBtn = document.getElementById('archive-btn');
    const compressBtn = document.getElementById('compress-btn');
    const uploadBtn = document.getElementById('upload-btn');
    const moveBtn = document.getElementById('move-btn');
    const copyBtn = document.getElementById('copy-btn');
    const renameBtn = document.getElementById('rename-btn');
    const inspectBtn = document.getElementById('inspect-btn');
    const extractCoversBtn = document.getElementById('extract-covers-btn');
    const deleteBtn = document.getElementById('delete-btn');

    const cloudMoveBtn = document.getElementById('cloud-move-btn');
    const cloudCopyBtn = document.getElementById('cloud-copy-btn');
    const cloudRenameBtn = document.getElementById('cloud-rename-btn');
    const cloudDeleteBtn = document.getElementById('cloud-delete-btn');
    const downloadBtn = document.getElementById('download-btn');

    if(browserMode === 'local') {
        if(newFolderBtn) newFolderBtn.disabled = false;
        if(repairBtn) repairBtn.disabled = !single;
        if(extractBtn) extractBtn.disabled = !single;
        if(archiveBtn) archiveBtn.disabled = !single;
        if(compressBtn) compressBtn.disabled = !single;
        if(renameBtn) renameBtn.disabled = !single;
        if(inspectBtn) inspectBtn.disabled = !has;
        if(extractCoversBtn) extractCoversBtn.disabled = !has;
        if(uploadBtn) uploadBtn.disabled = !has;
        if(moveBtn) moveBtn.disabled = !has;
        if(copyBtn) copyBtn.disabled = !has;
        if(deleteBtn) deleteBtn.disabled = !has;
    } else {
        if(newFolderBtn) newFolderBtn.disabled = !currentRemote;
        if(downloadBtn) downloadBtn.disabled = !has;
        if(cloudMoveBtn) cloudMoveBtn.disabled = !has;
        if(cloudCopyBtn) cloudCopyBtn.disabled = !has;
        if(cloudDeleteBtn) cloudDeleteBtn.disabled = !has;
        if(cloudRenameBtn) cloudRenameBtn.disabled = !single;
    }
}

// Initialize global namespace
window.files = window.files || {};

// --- Wire Events ---
document.addEventListener('DOMContentLoaded', () => {
    // Nav
    document.getElementById('refresh-btn').onclick = () => loadPath(currentPath);
    document.getElementById('select-all-check').onclick = () => {
        const checked = document.getElementById('select-all-check').checked;
        document.querySelectorAll('#file-list input[type="checkbox"]').forEach(cb => {
            cb.checked = checked;
            if(checked && cb.dataset.path) {
                if(!selectedPaths.includes(cb.dataset.path)) selectedPaths.push(cb.dataset.path);
            }
        });
        if(!checked) selectedPaths = [];
        updateButtonState();
    };

    // Local Actions
    document.getElementById('repair-btn').onclick = async () => {
         if(confirm(`Repair ${selectedPaths[0]}?`)) {
             await fetch('/api/repair', {
                 method: 'POST',
                 headers:{'Content-Type':'application/json'},
                 body: JSON.stringify({path: selectedPaths[0]})
             });
             showToast('Repair Queued', 'success');
         }
    };

    // Archive
    document.getElementById('archive-btn').onclick = async () => {
        if (typeof loadRemotesSelect === 'function') loadRemotesSelect(document.getElementById('arc-remote'));
        document.getElementById('arc-name').value = selectedPaths[0].split('/').pop();

        // Load preference
        const savedNaming = localStorage.getItem('arc-naming-pref');
        if(savedNaming) document.getElementById('arc-naming').value = savedNaming;

        // Trigger change to update visibility
        document.getElementById('arc-fmt').dispatchEvent(new Event('change'));

        document.getElementById('archive-modal').style.display = 'block';
    };

    document.getElementById('arc-fmt').onchange = (e) => {
        const isRar = e.target.value === 'rar';
        const is7z = e.target.value === '7z';
        const nameGrp = document.getElementById('arc-naming-group');
        const rrGrp = document.getElementById('arc-rr-group');

        // Hide Naming Scheme for RAR (it defaults to standard part1.rar)
        // Show Naming Scheme for 7z (if supported/requested)
        if(nameGrp) nameGrp.style.display = is7z ? 'block' : 'none';

        // Recovery Record only for RAR
        if(rrGrp) rrGrp.style.display = isRar ? 'block' : 'none';
    };

    document.getElementById('start-arc').onclick = async () => {
         const naming = document.getElementById('arc-naming').value;
         localStorage.setItem('arc-naming-pref', naming);

         document.getElementById('archive-modal').style.display = 'none';
         await fetch('/api/archive', {
             method:'POST',
             headers:{'Content-Type':'application/json'},
             body: JSON.stringify({
                 path: selectedPaths[0],
                 name: document.getElementById('arc-name').value,
                 split_size: document.getElementById('arc-size').value,
                 password: document.getElementById('arc-pass').value,
                 format: document.getElementById('arc-fmt').value,
                 naming_scheme: naming,
                 rar_recovery_record: document.getElementById('arc-rr').checked,
                 create_par2: document.getElementById('arc-par2').checked,
                 upload: document.getElementById('arc-upload').checked,
                 remote: document.getElementById('arc-remote').value,
                 upload_path: document.getElementById('arc-upload-path').value
             })
         });
         showToast('Pack Queued', 'success');
    };
    document.getElementById('arc-upload').onchange = (e) => {
        document.getElementById('arc-upload-opts').style.display = e.target.checked ? 'block' : 'none';
    };

    // Compress
    document.getElementById('compress-btn').onclick = () => {
        document.getElementById('comp-name').value = selectedPaths[0].split('/').pop();
        document.getElementById('comp-fmt').dispatchEvent(new Event('change'));
        document.getElementById('compress-modal').style.display = 'block';
    };

    document.getElementById('comp-fmt').onchange = (e) => {
        // Hide password for non-supported formats (tar, gz, bz2, iso)
        const val = e.target.value;
        const supportsPass = (val === '7z' || val === 'zip');
        const passGroup = document.getElementById('comp-pass-group');
        const passInput = document.getElementById('comp-pass');

        if (supportsPass) {
            passInput.disabled = false;
            passInput.placeholder = "Optional";
            passGroup.style.opacity = "1";
        } else {
            passInput.disabled = true;
            passInput.value = "";
            passInput.placeholder = "Not supported for " + val;
            passGroup.style.opacity = "0.5";
        }
    };

    document.getElementById('start-comp').onclick = async () => {
        document.getElementById('compress-modal').style.display = 'none';
        await fetch('/api/compress', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                path: selectedPaths[0],
                name: document.getElementById('comp-name').value,
                format: document.getElementById('comp-fmt').value,
                level: document.getElementById('comp-level').value,
                password: document.getElementById('comp-pass').value
            })
        });
        showToast('Compression Queued', 'success');
    };

    // Upload
    document.getElementById('upload-btn').onclick = () => {
        if (typeof loadRemotesSelect === 'function') loadRemotesSelect(document.getElementById('up-remote'));
        document.getElementById('upload-modal').style.display='block';
    };
    document.getElementById('start-up').onclick = async () => {
        document.getElementById('upload-modal').style.display='none';
        await fetch('/api/upload', {
            method:'POST',
            headers:{'Content-Type':'application/json'},
            body: JSON.stringify({
                paths: selectedPaths,
                remote: document.getElementById('up-remote').value,
                upload_path: document.getElementById('up-path').value,
                transfers: document.getElementById('up-transfers').value
            })
        });
        showToast('Upload Queued', 'success');
    };

    // Delete
    document.getElementById('delete-btn').onclick = async () => {
        if(confirm(`Delete ${selectedPaths.length} items?`)) {
            await fetch('/api/delete', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({paths:selectedPaths})});
            loadPath(currentPath);
            showToast('Deleted', 'success');
        }
    };

    // Extract
    document.getElementById('extract-btn').onclick = () => document.getElementById('extract-modal').style.display='block';
    document.getElementById('confirm-ext').onclick = async () => {
        document.getElementById('extract-modal').style.display='none';
        await fetch('/api/extract', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({path:selectedPaths[0], method:document.getElementById('ext-method').value, password:document.getElementById('ext-pass').value})});
        showToast('Extract Queued', 'success');
    };

    // Rename
    document.getElementById('rename-btn').onclick = () => {
        document.getElementById('rename-input').value=selectedPaths[0].split('/').pop();
        document.getElementById('rename-modal').style.display='block';
    };
    document.getElementById('confirm-rename').onclick = async () => {
        document.getElementById('rename-modal').style.display='none';
        const val = document.getElementById('rename-input').value;
        if(browserMode==='cloud') {
            await fetch('/api/rclone/rename', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({remote:currentRemote, path:selectedPaths[0], new_name:val})});
        } else {
            await fetch('/api/rename', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({path:selectedPaths[0], new_name:val})});
        }
        loadPath(currentPath);
    };

    // Mkdir
    document.getElementById('new-folder-btn').onclick = () => document.getElementById('mkdir-modal').style.display='block';
    document.getElementById('confirm-mkdir').onclick = async () => {
        document.getElementById('mkdir-modal').style.display='none';
        const val = document.getElementById('mkdir-name').value;
        if(browserMode==='cloud') {
            await fetch('/api/rclone/mkdir', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({remote:currentRemote, path:currentPath, name:val})});
        } else {
            await fetch('/api/mkdir', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({path:currentPath, name:val})});
        }
        loadPath(currentPath);
    };

    // Inspect
    document.getElementById('inspect-btn').onclick = async () => {
        const res = await fetch('/api/inspect', {
            method:'POST',
            headers:{'Content-Type':'application/json'},
            body:JSON.stringify({paths: selectedPaths})
        });
        const d = await res.json();
        renderInspectModal(d);
        document.getElementById('inspect-modal').style.display='block';
    };

    // Extract Covers (Attached to global window.files for onClick access from HTML)
    window.files.triggerExtractCovers = async () => {
        if(!confirm(`Extract covers from ${selectedPaths.length} items? (Recursively scans folders)`)) return;

        try {
            const res = await fetch('/api/media/extract-covers', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ paths: selectedPaths })
            });
            const data = await res.json();

            if(data.status === 'queued') {
                showToast(`Extraction Queued (Job ID: ${data.job_id})`, 'success');
            } else {
                showToast(data.error || "Failed to queue job", 'error');
            }
        } catch(e) {
            showToast("Request failed: " + e, 'error');
        }
    };

    function renderInspectModal(data) {
        const el = document.getElementById('inspect-content');
        el.innerHTML = '';

        if (data.type === 'unknown' && !data.details) { el.innerHTML = '<p>No details available.</p>'; return; }

        if (data.details) {
            const table = document.createElement('table');
            table.style.width = '100%';
            table.style.borderCollapse = 'collapse';
            table.style.marginBottom = '20px';
            data.details.forEach(([key, val]) => {
                table.innerHTML += `<tr><td style="color:#737aa2;padding:5px;border-bottom:1px solid #2f3549;width:120px;">${key}</td><td style="color:#c0caf5;padding:5px;border-bottom:1px solid #2f3549;">${val}</td></tr>`;
            });
            el.appendChild(table);
        }
        if (data.contents) {
            el.innerHTML += '<h4 style="color:#7aa2f7;margin-top:0;">Archive Contents:</h4>';
            const ul = document.createElement('ul'); ul.style.listStyle='none'; ul.style.padding='0';
            data.contents.forEach(item => {
                ul.innerHTML += `<li style="padding:4px 0;border-bottom:1px solid #2f3549;display:flex;justify-content:space-between;"><span>${item.name}</span> <span style="color:#565f89;">${item.size}</span></li>`;
            });
            el.appendChild(ul);
        }
    }

    // Move/Copy Buttons wired in cloud.js usually, but we need to ensure openMcModal is global
    document.getElementById('move-btn').onclick = () => openMcModal('move');
    document.getElementById('copy-btn').onclick = () => openMcModal('copy');

    // Init
    loadPath('');
});
