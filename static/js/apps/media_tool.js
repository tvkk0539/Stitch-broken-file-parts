// Media Toolbox App
const mediaTool = {
    // State
    currentFile: null,
    streams: [],

    init: function() {
        console.log("Media Tool Init");
    },

    selectFile: function() {
        // Open the generic file picker modal logic from main.js/files.js
        // We reuse the move-copy modal style or create a simple one?
        // Let's create a custom simple picker logic using existing backend.
        // Actually, we can reuse 'openMcModal' but context is tricky.
        // Better: A dedicated simple picker for Apps.
        openFilePickerForMedia();
    },

    loadAnalysis: async function(path) {
        this.currentFile = path;
        document.getElementById('mt-file-display').textContent = path;
        document.getElementById('mt-streams-container').innerHTML = '<div class="spinner-border"></div> Analyzing...';
        document.getElementById('mt-actions-panel').style.display = 'none';

        try {
            const res = await fetch('/api/media/streams', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({path: path})
            });
            const data = await res.json();

            if(data.error) throw new Error(data.error);

            this.renderStreams(data.streams);
            document.getElementById('mt-actions-panel').style.display = 'block';
        } catch(e) {
            document.getElementById('mt-streams-container').innerHTML = `<div style="color:var(--danger-color)">Error: ${e.message}</div>`;
        }
    },

    renderStreams: function(streams) {
        this.streams = streams;
        const container = document.getElementById('mt-streams-container');
        container.innerHTML = '';

        if(!streams || streams.length === 0) {
            container.innerHTML = 'No streams found.';
            return;
        }

        const table = document.createElement('table');
        table.className = 'data-table'; // Assume global style or add inline
        table.style.width = '100%';
        table.style.borderCollapse = 'collapse';

        table.innerHTML = `
            <thead>
                <tr style="border-bottom:1px solid var(--border-color); text-align:left; color:var(--text-muted);">
                    <th style="padding:10px; width:40px;">Extract</th>
                    <th style="padding:10px;">ID</th>
                    <th style="padding:10px;">Type</th>
                    <th style="padding:10px;">Codec</th>
                    <th style="padding:10px;">Language</th>
                    <th style="padding:10px;">Details</th>
                </tr>
            </thead>
            <tbody></tbody>
        `;

        const tbody = table.querySelector('tbody');

        streams.forEach(s => {
            const tr = document.createElement('tr');
            tr.style.borderBottom = '1px solid #2f334d';

            let icon = '❓';
            if(s.type==='video') icon = '🎬';
            if(s.type==='audio') icon = '🔊';
            if(s.type==='subtitle') icon = '💬';

            // Auto-check logic? Maybe default off.

            tr.innerHTML = `
                <td style="padding:10px; text-align:center;">
                    <input type="checkbox" class="stream-check" data-idx="${s.index}" style="transform:scale(1.2);">
                </td>
                <td style="padding:10px; font-family:monospace;">${s.index}</td>
                <td style="padding:10px;">${icon} ${s.type.toUpperCase()}</td>
                <td style="padding:10px; color:var(--accent-color);">${s.codec}</td>
                <td style="padding:10px;">${s.lang}</td>
                <td style="padding:10px; font-size:0.9em; color:var(--text-muted);">
                    ${s.title || ''}
                    ${s.width ? s.width+'x'+s.height : ''}
                    ${s.channels ? s.channels+'ch' : ''}
                </td>
            `;
            tbody.appendChild(tr);
        });

        container.appendChild(table);
    },

    extractSelected: async function() {
        const checks = document.querySelectorAll('.stream-check:checked');
        if(checks.length === 0) {
            showToast("Please select at least one stream", "error");
            return;
        }

        const selections = [];
        checks.forEach(cb => {
            const idx = parseInt(cb.dataset.idx);
            const s = this.streams.find(x => x.index === idx);
            if(s) selections.push(s);
        });

        try {
            const res = await fetch('/api/media/extract-streams', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    path: this.currentFile,
                    selections: selections
                })
            });
            const data = await res.json();

            if(data.status === 'queued') {
                showToast(`Extraction Queued (Job ${data.job_id})`, 'success');
                // Switch to Queue view? Optional.
            } else {
                showToast(data.error || "Failed", "error");
            }
        } catch(e) {
            showToast(e.message, "error");
        }
    }
};

// Simple File Picker for Media Tool (Global function to be called from HTML)
let mtPickerCallback = null;
function openFilePickerForMedia() {
    // Reuse the GH Picker modal structure or create new?
    // Let's reuse 'gh-upload-modal' logic but adapt it.
    // Actually, let's create a dynamic modal in HTML or reuse 'move-copy-modal' logic.
    // 'move-copy-modal' is for folders mainly.
    // Let's use the 'gh-browser-modal' structure? No, that's for Repo browsing.

    // Simplest: Use 'gh-upload-modal' logic but for local file picking.
    // We already have 'openGhServerPicker' which sets 'ghServerPickerCallback'.
    // Let's hook into that if possible, or duplicate the simple picker logic.

    // I'll assume we add a 'media-file-picker' modal in HTML step.
    document.getElementById('media-file-picker').style.display = 'block';
    loadMediaPickerPath('');
}

async function loadMediaPickerPath(path) {
    const list = document.getElementById('mfp-list');
    const bread = document.getElementById('mfp-path');
    list.innerHTML = 'Loading...';
    bread.textContent = path || '/';

    try {
        const res = await fetch(`/api/list?path=${encodeURIComponent(path)}`);
        const data = await res.json();

        list.innerHTML = '';
        if(data.parent_path !== null) {
            const li = document.createElement('div');
            li.className = 'picker-item';
            li.innerHTML = '📁 ..';
            li.onclick = () => loadMediaPickerPath(data.parent_path);
            list.appendChild(li);
        }

        data.items.forEach(item => {
            const div = document.createElement('div');
            div.className = 'picker-item';
            div.style.padding = '8px';
            div.style.cursor = 'pointer';
            div.style.borderBottom = '1px solid #333';

            if(item.is_dir) {
                div.innerHTML = `📁 ${item.name}`;
                div.onclick = () => loadMediaPickerPath(item.path);
            } else {
                // Filter video files
                if(/\.(mkv|mp4|avi|mov|ts|m2ts|webm)$/i.test(item.name)) {
                    div.innerHTML = `🎬 ${item.name}`;
                    div.style.color = '#bb9af7';
                    div.onclick = () => {
                        document.getElementById('media-file-picker').style.display = 'none';
                        mediaTool.loadAnalysis(item.path);
                    };
                } else {
                    div.innerHTML = `<span style="opacity:0.5">📄 ${item.name}</span>`;
                    div.style.cursor = 'default';
                }
            }
            list.appendChild(div);
        });
    } catch(e) { list.textContent = 'Error loading files'; }
}
