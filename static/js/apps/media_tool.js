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

        // Update Source Inspector
        document.getElementById('mt-file-name').textContent = path.split('/').pop();
        document.getElementById('mt-file-meta').textContent = path;
        document.getElementById('mt-tech-specs').style.display = 'none';

        document.getElementById('mt-streams-container').innerHTML = `
            <div style="display:flex; flex-direction:column; align-items:center; justify-content:center; height:100%; color:var(--text-muted);">
                <div class="spinner-border" style="margin-bottom:15px;"></div>
                <p>Analyzing container structure...</p>
            </div>
        `;
        document.getElementById('mt-actions-panel').style.display = 'none';

        try {
            const res = await fetch('/api/media/streams', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({path: path})
            });
            const data = await res.json();

            if(data.error) throw new Error(data.error);

            this.renderInspector(data.format, data.streams);
            this.renderStreams(data.streams);
            document.getElementById('mt-actions-panel').style.display = 'block';
        } catch(e) {
            document.getElementById('mt-streams-container').innerHTML = `
                <div style="display:flex; flex-direction:column; align-items:center; justify-content:center; height:100%; color:var(--danger-color);">
                    <div style="font-size:3em; margin-bottom:10px;">❌</div>
                    <p>Analysis Failed: ${e.message}</p>
                </div>
            `;
        }
    },

    renderInspector: function(format, streams) {
        const specs = document.getElementById('mt-tech-specs');
        specs.style.display = 'block';

        // Format
        document.getElementById('mt-spec-format').textContent = format.format_long_name || format.format_name || 'Unknown';

        // Duration
        const dur = parseFloat(format.duration);
        let durStr = '-';
        if(!isNaN(dur)) {
            const h = Math.floor(dur / 3600);
            const m = Math.floor((dur % 3600) / 60);
            const s = Math.floor(dur % 60);
            durStr = `${h}h ${m}m ${s}s`;
        }
        document.getElementById('mt-spec-duration').textContent = durStr;

        // Bitrate
        const br = parseInt(format.bit_rate);
        let brStr = '-';
        if(!isNaN(br)) {
            brStr = (br / 1000000).toFixed(1) + ' Mb/s';
        }
        document.getElementById('mt-spec-bitrate').textContent = brStr;

        // Streams Count
        document.getElementById('mt-spec-streams').textContent = streams.length;
    },

    renderStreams: function(streams) {
        this.streams = streams;
        const container = document.getElementById('mt-streams-container');
        container.innerHTML = '';

        if(!streams || streams.length === 0) {
            container.innerHTML = '<div style="padding:20px; text-align:center; color:var(--text-muted);">No streams found.</div>';
            return;
        }

        // Simple XSS Protection
        const escape = (str) => {
            if(!str) return '';
            return String(str)
                .replace(/&/g, "&amp;")
                .replace(/</g, "&lt;")
                .replace(/>/g, "&gt;")
                .replace(/"/g, "&quot;")
                .replace(/'/g, "&#039;");
        };

        const table = document.createElement('table');
        table.style.width = '100%';
        table.style.borderCollapse = 'collapse';

        table.innerHTML = `
            <thead>
                <tr style="border-bottom:1px solid #2f334d; text-align:left; color:var(--text-muted); background:#1a1b26; font-size:0.9em;">
                    <th style="padding:12px 15px; width:40px;">#</th>
                    <th style="padding:12px 15px;">Type</th>
                    <th style="padding:12px 15px;">Codec</th>
                    <th style="padding:12px 15px;">Language</th>
                    <th style="padding:12px 15px;">Details</th>
                    <th style="padding:12px 15px; text-align:center;">Extract</th>
                </tr>
            </thead>
            <tbody></tbody>
        `;

        const tbody = table.querySelector('tbody');

        streams.forEach(s => {
            const tr = document.createElement('tr');
            tr.style.borderBottom = '1px solid #1f2335';
            tr.style.cursor = 'pointer';

            // Hover effect logic handled by CSS usually, but inline for now
            tr.onmouseover = () => tr.style.background = '#1f2335';
            tr.onmouseout = () => tr.style.background = 'transparent';

            let icon = '❓';
            let color = 'inherit';

            if(s.type==='video') { icon = '🎬'; color = '#7aa2f7'; }
            if(s.type==='audio') { icon = '🔊'; color = '#9ece6a'; }
            if(s.type==='subtitle') { icon = '💬'; color = '#e0af68'; }

            // Row click toggles checkbox
            tr.onclick = (e) => {
                if(e.target.type !== 'checkbox') {
                    const cb = tr.querySelector('.stream-check');
                    if(cb) cb.checked = !cb.checked;
                }
            };

            tr.innerHTML = `
                <td style="padding:12px 15px; font-family:monospace; color:var(--text-muted);">${s.index}</td>
                <td style="padding:12px 15px; color:${color}; font-weight:500;">${icon} ${s.type.toUpperCase()}</td>
                <td style="padding:12px 15px; font-family:monospace;">${escape(s.codec)}</td>
                <td style="padding:12px 15px;">${s.lang !== 'und' ? escape(s.lang.toUpperCase()) : '<span style="opacity:0.3">-</span>'}</td>
                <td style="padding:12px 15px; font-size:0.9em; color:var(--text-muted);">
                    ${escape(s.title || '')}
                    ${s.width ? s.width+'x'+s.height : ''}
                    ${s.channels ? s.channels+'ch' : ''}
                </td>
                <td style="padding:12px 15px; text-align:center;">
                    <input type="checkbox" class="stream-check" data-idx="${s.index}" style="transform:scale(1.2); cursor:pointer;">
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
