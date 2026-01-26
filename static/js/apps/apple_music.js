// Apple Music Downloader App Logic

const appleMusic = {
    state: {
        currentAlbum: null,
        queue: [],
        config: null,
        wrapperPollInterval: null
    },

    // Schema mapping for "Professional" UI generation
    configSchema: {
        // Authentication
        'media-user-token': { label: 'Media User Token', type: 'password', group: 'Authentication' },
        'authorization-token': { label: 'Authorization Token', type: 'password', group: 'Authentication' },
        'storefront': { label: 'Storefront (Region)', type: 'text', placeholder: 'us, jp, de...', group: 'Authentication' },
        'language': { label: 'Language', type: 'text', placeholder: 'en-US', group: 'Authentication' },

        // Download Settings
        'alac-save-folder': { label: 'ALAC Save Folder', type: 'text', group: 'Downloads' },
        'atmos-save-folder': { label: 'Atmos Save Folder', type: 'text', group: 'Downloads' },
        'aac-save-folder': { label: 'AAC Save Folder', type: 'text', group: 'Downloads' },
        'limit-max': { label: 'Max Download Limit', type: 'number', group: 'Downloads' },
        'max-memory-limit': { label: 'Max Memory Limit (MB)', type: 'number', group: 'Downloads' },

        // Quality & Formats
        'aac-type': { label: 'AAC Type', type: 'select', options: ['aac-lc', 'aac', 'aac-binaural', 'aac-downmix'], group: 'Quality' },
        'alac-max': { label: 'ALAC Max Rate', type: 'select', options: ['192000', '96000', '48000', '44100'], group: 'Quality' },
        'atmos-max': { label: 'Atmos Max', type: 'select', options: ['2768', '2448'], group: 'Quality' },
        'mv-audio-type': { label: 'Music Video Audio', type: 'select', options: ['atmos', 'ac3', 'aac'], group: 'Quality' },
        'mv-max': { label: 'Music Video Max Quality', type: 'select', options: ['2160', '1080', '720'], group: 'Quality' },

        // Metadata & Lyrics
        'embed-cover': { label: 'Embed Cover Art', type: 'bool', group: 'Metadata' },
        'save-artist-cover': { label: 'Save Artist Cover', type: 'bool', group: 'Metadata' },
        'cover-format': { label: 'Cover Format', type: 'select', options: ['jpg', 'png', 'original'], group: 'Metadata' },
        'embed-lrc': { label: 'Embed Lyrics', type: 'bool', group: 'Metadata' },
        'save-lrc-file': { label: 'Save Lyrics File (.lrc)', type: 'bool', group: 'Metadata' },
        'lrc-type': { label: 'Lyrics Type', type: 'select', options: ['lyrics', 'syllable-lyrics'], group: 'Metadata' },
        'lrc-format': { label: 'Lyrics Format', type: 'select', options: ['lrc', 'ttml'], group: 'Metadata' },

        // Conversion
        'convert-after-download': { label: 'Convert After Download', type: 'bool', group: 'Conversion' },
        'convert-format': { label: 'Target Format', type: 'select', options: ['flac', 'mp3', 'opus', 'wav', 'copy'], group: 'Conversion' },
        'convert-keep-original': { label: 'Keep Original File', type: 'bool', group: 'Conversion' }
    },

    init: () => {
        console.log("Apple Music App Initialized");
    },

    open: () => {
        switchView('apple-music');
        appleMusic.switchTab('down'); // Default tab
    },

    switchTab: (tab) => {
        // Tabs: 'down', 'config', 'wrapper', 'setup'
        document.querySelectorAll('.browser-tab').forEach(b => b.classList.remove('active'));
        const tabBtn = document.getElementById(`am-tab-${tab}`);
        if(tabBtn) tabBtn.classList.add('active');

        document.getElementById('am-view-down').style.display = 'none';
        document.getElementById('am-view-setup').style.display = 'none';
        document.getElementById('am-view-config').style.display = 'none';
        document.getElementById('am-view-wrapper').style.display = 'none';

        document.getElementById(`am-view-${tab}`).style.display = 'block';

        // Clear wrapper interval if leaving wrapper tab
        if (appleMusic.state.wrapperPollInterval) {
            clearInterval(appleMusic.state.wrapperPollInterval);
            appleMusic.state.wrapperPollInterval = null;
        }

        if (tab === 'config') {
            appleMusic.loadConfig();
        } else if (tab === 'wrapper') {
            appleMusic.checkWrapperStatus();
            appleMusic.state.wrapperPollInterval = setInterval(appleMusic.checkWrapperStatus, 2000);
        }
    },

    // --- WRAPPER LOGIC ---

    checkWrapperStatus: async () => {
        try {
            const res = await fetch('/api/apps/apple-music/wrapper/status');
            const status = await res.json();

            // 1. Update State Badges
            const badge = document.getElementById('am-wrap-state');
            const pidDisplay = document.getElementById('am-wrap-pid');

            if (status.running) {
                badge.className = 'badge badge-success';
                badge.innerText = 'RUNNING';
                pidDisplay.innerText = status.pid;
            } else {
                badge.className = 'badge badge-gray';
                badge.innerText = 'STOPPED';
                pidDisplay.innerText = '-';
            }

            // 2. Update Panels based on Install state
            if (status.installed) {
                document.getElementById('am-wrap-install-card').style.display = 'none';
                document.getElementById('am-wrap-control-card').style.display = 'block';
            } else {
                document.getElementById('am-wrap-install-card').style.display = 'block';
                document.getElementById('am-wrap-control-card').style.display = 'none';
            }

            // 3. Toggle Start/Stop Buttons
            if (status.running) {
                document.getElementById('am-wrap-start-btn').style.display = 'none';
                document.getElementById('am-wrap-stop-btn').style.display = 'block';
            } else {
                document.getElementById('am-wrap-start-btn').style.display = 'block';
                document.getElementById('am-wrap-stop-btn').style.display = 'none';
            }

            // 4. Update Logs
            const consoleDiv = document.getElementById('am-wrap-console');
            if (status.logs && status.logs.length > 0) {
                consoleDiv.innerText = status.logs.join('\n');
                // Auto scroll to bottom
                consoleDiv.scrollTop = consoleDiv.scrollHeight;
            } else if (!status.running) {
                consoleDiv.innerHTML = '<span style="color:var(--text-muted);">Process stopped. Waiting for output...</span>';
            }

        } catch (e) {
            console.error("Wrapper status poll failed", e);
        }
    },

    installWrapper: async () => {
        if (!confirm("Download and install the Wrapper binary (~50MB)?")) return;

        try {
            const res = await fetch('/api/apps/apple-music/wrapper/install', {method: 'POST'});
            const json = await res.json();
            if (json.status === 'queued') {
                showToast("Installation Queued", "success");
            } else {
                showToast("Install failed", "error");
            }
        } catch (e) {
            showToast("Error: " + e, "error");
        }
    },

    startWrapper: async () => {
        const user = document.getElementById('am-wrap-user').value.trim();
        const pass = document.getElementById('am-wrap-pass').value.trim();

        if (!user || !pass) {
            showToast("Username and Password required", "error");
            return;
        }

        try {
            const res = await fetch('/api/apps/apple-music/wrapper/start', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({username: user, password: pass})
            });
            const json = await res.json();

            if (json.status === 'started') {
                showToast("Wrapper Service Started", "success");
                appleMusic.checkWrapperStatus();
            } else {
                showToast("Start failed: " + json.error, "error");
            }
        } catch (e) {
            showToast("Error: " + e, "error");
        }
    },

    stopWrapper: async () => {
        if(!confirm("Stop the wrapper service?")) return;

        await fetch('/api/apps/apple-music/wrapper/stop', {method: 'POST'});
        showToast("Service Stopped", "success");
        appleMusic.checkWrapperStatus();
    },

    sendWrapperInput: async () => {
        const input = document.getElementById('am-wrap-input');
        const text = input.value.trim();
        if (!text) return;

        try {
            const res = await fetch('/api/apps/apple-music/wrapper/input', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({text: text})
            });

            // Clear input immediately for better UX
            input.value = '';

            const json = await res.json();
            if (json.status === 'sent') {
                // Manually append to log for instant feedback
                const consoleDiv = document.getElementById('am-wrap-console');
                consoleDiv.innerText += `\n[UI Input] ${text}`;
                consoleDiv.scrollTop = consoleDiv.scrollHeight;
            } else {
                showToast("Send failed: " + json.error, "error");
            }
        } catch (e) {
            showToast("Error: " + e, "error");
        }
    },

    // --- CONFIGURATION LOGIC ---

    loadConfig: async () => {
        const loader = document.getElementById('am-config-loader');
        const form = document.getElementById('am-config-form');
        const err = document.getElementById('am-config-error');
        const pathDisplay = document.getElementById('am-config-path');

        loader.style.display = 'block';
        form.style.display = 'none';
        err.style.display = 'none';
        pathDisplay.innerText = '';

        try {
            const res = await fetch('/api/apps/apple-music/config');
            const json = await res.json();

            loader.style.display = 'none';

            if (json.error) {
                err.innerText = json.error;
                err.style.display = 'block';
                return;
            }

            appleMusic.state.config = json.data;
            pathDisplay.innerText = `File: ${json.path}`;
            form.style.display = 'grid';

            appleMusic.renderConfigForm(json.data);

        } catch (e) {
            loader.style.display = 'none';
            err.innerText = "Network Error: " + e;
            err.style.display = 'block';
        }
    },

    renderConfigForm: (data) => {
        const container = document.getElementById('am-config-form');
        container.innerHTML = '';

        // Group data by schema groups
        const groups = {};

        // 1. Process Schema fields first (Ordered)
        for (const [key, schema] of Object.entries(appleMusic.configSchema)) {
            if (key in data) {
                const gName = schema.group || 'Other';
                if (!groups[gName]) groups[gName] = [];
                groups[gName].push({ key, value: data[key], schema });
            }
        }

        // 2. Process Remaining fields (Unkown/Extra)
        for (const [key, value] of Object.entries(data)) {
            if (!appleMusic.configSchema[key]) {
                const gName = 'Advanced / Other';
                if (!groups[gName]) groups[gName] = [];
                groups[gName].push({ key, value, schema: { label: key, type: typeof value === 'boolean' ? 'bool' : 'text' } });
            }
        }

        // Render Groups
        for (const [groupName, fields] of Object.entries(groups)) {
            const groupDiv = document.createElement('div');
            groupDiv.className = 'config-group-card';
            groupDiv.style.cssText = `
                background: var(--bg-dark);
                border: 1px solid var(--border-color);
                padding: 15px;
                border-radius: 6px;
                display: flex;
                flex-direction: column;
                gap: 15px;
            `;

            groupDiv.innerHTML = `<h4 style="margin:0 0 10px 0; color:var(--accent-color); border-bottom:1px solid var(--border-color); padding-bottom:5px;">${groupName}</h4>`;

            fields.forEach(field => {
                const formGroup = document.createElement('div');
                formGroup.className = 'form-group';
                formGroup.style.marginBottom = '0';

                const label = document.createElement('label');
                label.innerText = field.schema.label || field.key;
                label.style.fontSize = '0.9em';

                let input;

                if (field.schema.type === 'bool') {
                    // Toggle Switch UI
                    formGroup.style.display = 'flex';
                    formGroup.style.justifyContent = 'space-between';
                    formGroup.style.alignItems = 'center';

                    label.style.margin = '0'; // reset default margin

                    const toggleLabel = document.createElement('label');
                    toggleLabel.className = 'switch'; // Assuming CSS support or I style it inline
                    // Simple Checkbox fallback if no switch css
                    input = document.createElement('input');
                    input.type = 'checkbox';
                    input.checked = field.value === true;
                    input.dataset.key = field.key;

                    toggleLabel.appendChild(input);
                    // Add text "Enabled" maybe?

                    formGroup.appendChild(label);
                    formGroup.appendChild(input); // Direct append for now

                } else if (field.schema.type === 'select') {
                    input = document.createElement('select');
                    input.dataset.key = field.key;
                    input.style.width = '100%';
                    input.style.padding = '8px';
                    input.style.background = '#13141c';
                    input.style.border = '1px solid var(--border-color)';
                    input.style.color = 'var(--text-color)';
                    input.style.borderRadius = '4px';

                    field.schema.options.forEach(opt => {
                        const option = document.createElement('option');
                        option.value = opt;
                        option.innerText = opt;
                        if (String(field.value) === String(opt)) option.selected = true;
                        input.appendChild(option);
                    });

                    formGroup.appendChild(label);
                    formGroup.appendChild(input);

                } else {
                    // Text / Password / Number
                    input = document.createElement('input');
                    input.type = field.schema.type === 'password' ? 'text' : field.schema.type; // Show passwords for config editing? Or keep hidden?
                    // Usually configs are secrets, let's keep it password but add toggle?
                    // For simplicity, lets use 'text' but maybe style it?
                    // Actually, 'password' input is annoying to edit. Let's use text for now as user likely needs to paste tokens.
                    if (field.schema.type === 'password') input.type = 'text';

                    input.value = field.value === null ? '' : field.value;
                    input.dataset.key = field.key;
                    input.placeholder = field.schema.placeholder || '';

                    // Style
                    input.style.width = '100%';
                    input.style.padding = '8px';
                    input.style.background = '#13141c';
                    input.style.border = '1px solid var(--border-color)';
                    input.style.color = '#c0caf5';
                    input.style.borderRadius = '4px';
                    input.style.boxSizing = 'border-box'; // Fix width overflow

                    formGroup.appendChild(label);
                    formGroup.appendChild(input);
                }

                groupDiv.appendChild(formGroup);
            });

            container.appendChild(groupDiv);
        }
    },

    saveConfig: async () => {
        const btn = document.querySelector('#am-view-config .purple-btn');
        const originalText = btn.innerText;
        btn.innerText = 'Saving...';
        btn.disabled = true;

        // Gather Data
        const updates = {};
        const inputs = document.querySelectorAll('#am-config-form [data-key]');

        inputs.forEach(input => {
            const key = input.dataset.key;
            let value;
            if (input.type === 'checkbox') {
                value = input.checked;
            } else {
                value = input.value;
                // Try number conversion if it looks like a number and was originally a number?
                // For now backend handles basic int conversion if existing is int.
            }
            updates[key] = value;
        });

        try {
            const res = await fetch('/api/apps/apple-music/config', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(updates)
            });
            const json = await res.json();

            if (json.status === 'success') {
                showToast("Configuration Saved!", "success");
            } else {
                showToast("Save Failed: " + (json.error || "Unknown"), "error");
            }
        } catch (e) {
            showToast("Network Error: " + e, "error");
        } finally {
            btn.innerText = originalText;
            btn.disabled = false;
        }
    },

    // --- IMPORT / SETUP LOGIC ---

    installRecommended: () => {
        const url = "https://github.com/zhaarey/apple-music-downloader.git";
        appleMusic.handleImportRepo(url);
    },

    handleImportRepo: async (targetUrl = null) => {
        const url = targetUrl || document.getElementById('am-setup-url').value.trim();
        if (!url) {
            showToast("Please enter a Repository URL", "error");
            return;
        }

        // Validate basic git url structure
        if (!url.startsWith('http') || (!url.endsWith('.git') && !targetUrl)) {
            if (!confirm("URL doesn't look like a standard git clone URL (usually ends in .git). Continue?")) return;
        }

        // Extract Name for subfolder
        let name = url.split('/').pop().replace('.git', '');
        if (!name) name = "repo_" + Date.now();

        const destPath = `Apple Music/${name}`;

        if (!confirm(`Import repository to:\n/data/downloads/${destPath}\n\nProceed?`)) return;

        try {
            const res = await fetch('/api/apps/github/repo/clone', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    url: url,
                    path: destPath,
                    account_id: null // Generic/Public clone
                })
            });

            const data = await res.json();
            if (data.status === 'queued') {
                showToast(`Clone Job Queued (Job ID: ${data.job_id})`, 'success');
                // Switch to queue to show user
                if (confirm("Job started. View progress in Queue?")) {
                    switchView('queue');
                }
            } else {
                showToast("Failed to queue job: " + (data.error || "Unknown error"), "error");
            }
        } catch (e) {
            showToast("Request Failed: " + e, "error");
        }
    },

    // --- MOCK DOWNLOADER LOGIC ---
    handleFetch: async () => {
        const url = document.getElementById('am-url-input').value;
        if (!url) {
            showToast("Please enter an Apple Music URL", "error");
            return;
        }

        const btn = document.getElementById('am-fetch-btn');
        const originalText = btn.innerHTML;
        btn.innerHTML = '<span class="spinner-border"></span> Fetching...';
        btn.disabled = true;

        // Mockup Simulation for UI UX Phase
        setTimeout(() => {
            appleMusic.mockFetchSuccess(url);
            btn.innerHTML = originalText;
            btn.disabled = false;
        }, 1000);
    },

    mockFetchSuccess: (url) => {
        // Simulating a result for UI testing
        const mockData = {
            title: "Hit Me Hard and Soft",
            artist: "Billie Eilish",
            year: "2024",
            cover: "https://is1-ssl.mzstatic.com/image/thumb/Music211/v4/4a/92/7d/4a927d73-2c13-e74f-90f7-6c84c6799d16/196589165243.jpg/600x600bb.jpg",
            tracks: [
                "Skinny", "Lunch", "Chihiro", "Birds of a Feather", "Wildflower", "The Greatest"
            ]
        };

        appleMusic.renderResult(mockData);
    },

    renderResult: (data) => {
        const container = document.getElementById('am-results-area');
        container.style.display = 'flex';

        // Populate
        document.getElementById('am-cover-img').src = data.cover;
        document.getElementById('am-album-title').textContent = data.title;
        document.getElementById('am-album-artist').textContent = data.artist;
        document.getElementById('am-album-meta').textContent = `${data.year} • ${data.tracks.length} Tracks`;

        const trackList = document.getElementById('am-tracklist');
        trackList.innerHTML = '';
        data.tracks.forEach((t, i) => {
            const row = document.createElement('div');
            row.className = 'am-track-row';
            row.innerHTML = `
                <span style="color:var(--text-muted); width:20px;">${i+1}</span>
                <span style="flex:1;">${t}</span>
                <input type="checkbox" checked title="Download this track">
            `;
            trackList.appendChild(row);
        });
    },

    addToQueue: () => {
        const url = document.getElementById('am-url-input').value;
        if (!url) return;

        showToast("Added to Download Queue", "success");

        // clear input
        document.getElementById('am-url-input').value = '';
        document.getElementById('am-results-area').style.display = 'none';

        // Add to UI Queue (Mock)
        const qContainer = document.getElementById('am-queue-list');
        const item = document.createElement('div');
        item.className = 'am-queue-item';
        item.innerHTML = `
            <div>
                <div style="font-weight:bold;">${document.getElementById('am-album-title').textContent}</div>
                <div style="font-size:0.8em; color:var(--text-muted);">Queued</div>
            </div>
            <div style="color:var(--accent-color);">Waiting...</div>
        `;
        qContainer.prepend(item);
    }
};

// Expose globally
window.appleMusic = appleMusic;
window.openAppleMusicApp = appleMusic.open;
