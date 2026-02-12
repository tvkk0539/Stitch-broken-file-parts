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
        // Naming Templates (with Variable Builder)
        'album-folder-format': { label: 'Album Folder Format', type: 'template', group: 'Naming & Formatting' },
        'playlist-folder-format': { label: 'Playlist Folder Format', type: 'template', group: 'Naming & Formatting' },
        'song-file-format': { label: 'Song File Format', type: 'template', group: 'Naming & Formatting' },
        'artist-folder-format': { label: 'Artist Folder Format', type: 'template', group: 'Naming & Formatting' },

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

    // Allowed Variables for Templates
    templateVariables: {
        'album-folder-format': ['{AlbumId}', '{AlbumName}', '{ArtistName}', '{ReleaseDate}', '{ReleaseYear}', '{UPC}', '{Copyright}', '{Quality}', '{Codec}', '{Tag}', '{RecordLabel}'],
        'playlist-folder-format': ['{PlaylistId}', '{PlaylistName}', '{ArtistName}', '{Quality}', '{Codec}', '{Tag}'],
        'song-file-format': ['{SongId}', '{SongNumer}', '{SongName}', '{DiscNumber}', '{TrackNumber}', '{Quality}', '{Codec}', '{Tag}'],
        'artist-folder-format': ['{ArtistId}', '{ArtistName}', '{UrlArtistName}']
    },

    init: () => {
        console.log("Apple Music App Initialized");
    },

    open: () => {
        switchView('apple-music');
        appleMusic.switchTab('down'); // Default tab
    },

    switchTab: (tab) => {
        // Tabs: 'down', 'queue', 'history', 'console', 'config', 'wrapper', 'setup'
        document.querySelectorAll('.browser-tab').forEach(b => b.classList.remove('active'));
        const tabBtn = document.getElementById(`am-tab-${tab}`);
        if(tabBtn) tabBtn.classList.add('active');

        ['down', 'queue', 'history', 'console', 'setup', 'config', 'wrapper'].forEach(t => {
            const el = document.getElementById(`am-view-${t}`);
            if(el) el.style.display = 'none';
        });

        document.getElementById(`am-view-${tab}`).style.display = 'block';

        // Clear wrapper interval if leaving wrapper tab
        if (appleMusic.state.wrapperPollInterval) {
            clearInterval(appleMusic.state.wrapperPollInterval);
            appleMusic.state.wrapperPollInterval = null;
        }

        // Stop console poll if leaving console (optional, saves bandwidth)
        if (tab !== 'console' && appleMusic.downloaderPollInterval) {
             clearInterval(appleMusic.downloaderPollInterval);
             appleMusic.downloaderPollInterval = null;
        }

        // Queue Poll (Active & History share data but separate views)
        if (tab === 'queue' || tab === 'history') {
            appleMusic.loadQueue(); // Poll immediately
            // Only auto-poll active queue for updates
            if (tab === 'queue' && !appleMusic.queuePollInterval) {
                appleMusic.queuePollInterval = setInterval(appleMusic.loadQueue, 2000);
            }
        }

        if (tab !== 'queue' && appleMusic.queuePollInterval) {
            clearInterval(appleMusic.queuePollInterval);
            appleMusic.queuePollInterval = null;
        }

        if (tab === 'config') {
            appleMusic.loadConfig();
        } else if (tab === 'wrapper') {
            appleMusic.checkWrapperStatus();
            appleMusic.state.wrapperPollInterval = setInterval(appleMusic.checkWrapperStatus, 2000);
        } else if (tab === 'console') {
            appleMusic.startConsolePoll();
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

    installWrapper: async (isCustom = false) => {
        let url = null;
        let confirmMsg = "Download and install the Wrapper binary (~50MB)?";

        if (isCustom) {
            url = document.getElementById('am-wrap-custom-url').value.trim();
            if (!url) {
                showToast("Please enter a URL", "error");
                return;
            }
            confirmMsg = `Install wrapper from custom URL?\n${url}`;
        }

        if (!confirm(confirmMsg)) return;

        try {
            const res = await fetch('/api/apps/apple-music/wrapper/install', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ url: url })
            });
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

    // Helper: Insert text at cursor position in an input
    insertAtCursor: (input, text) => {
        if (!input) return;
        const start = input.selectionStart;
        const end = input.selectionEnd;
        const val = input.value;
        input.value = val.substring(0, start) + text + val.substring(end);
        input.selectionStart = input.selectionEnd = start + text.length;
        input.focus();
    },

    renderTemplateBuilder: (key, value, variables) => {
        const container = document.createElement('div');

        // Input
        const input = document.createElement('input');
        input.type = 'text';
        input.value = value || '';
        input.dataset.key = key; // Ensure dataset.key is set for saveConfig
        input.id = `am-config-${key}`; // Add ID for robustness
        input.className = 'am-template-input';
        input.style.width = '100%';
        input.style.padding = '10px';
        input.style.background = '#13141c';
        input.style.border = '1px solid var(--border-color)';
        input.style.color = '#7aa2f7'; // Distinct color for templates
        input.style.fontFamily = 'monospace';
        input.style.borderRadius = '4px';
        input.style.marginBottom = '8px';
        input.style.boxSizing = 'border-box';
        input.placeholder = '{ArtistName} - {AlbumName}';

        // Variable Cloud
        const cloud = document.createElement('div');
        cloud.style.display = 'flex';
        cloud.style.flexWrap = 'wrap';
        cloud.style.gap = '6px';

        variables.forEach(v => {
            const pill = document.createElement('span');
            pill.innerText = v;
            pill.style.background = '#24283b';
            pill.style.color = '#c0caf5';
            pill.style.border = '1px solid #414868';
            pill.style.borderRadius = '4px';
            pill.style.padding = '2px 6px';
            pill.style.fontSize = '0.8em';
            pill.style.cursor = 'pointer';
            pill.style.fontFamily = 'monospace';
            pill.style.transition = 'background 0.2s';

            pill.onmouseover = () => pill.style.background = '#414868';
            pill.onmouseout = () => pill.style.background = '#24283b';
            pill.onclick = () => appleMusic.insertAtCursor(input, v);

            cloud.appendChild(pill);
        });

        container.appendChild(input);
        container.appendChild(cloud);
        return container;
    },

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

        // --- Manual Sync Controls ---
        const syncCard = document.createElement('div');
        syncCard.className = 'config-group-card';
        syncCard.style.cssText = `
            background: var(--bg-dark);
            border: 1px solid var(--accent-color);
            padding: 15px;
            border-radius: 6px;
            display: flex;
            flex-direction: column;
            gap: 10px;
            margin-bottom: 20px;
        `;
        syncCard.innerHTML = `
            <h4 style="margin:0; color:var(--accent-color); font-size:1em;">Database Management (Manual Sync)</h4>
            <div style="display:flex; gap:10px; flex-wrap:wrap;">
                <button class="btn" onclick="appleMusic.syncImport()" style="flex:1; border:1px solid #414868; background:#1a1b26;">
                    📥 Import (Config File &rarr; DB)
                </button>
                <button class="btn" onclick="appleMusic.syncExport()" style="flex:1; border:1px solid #414868; background:#1a1b26;">
                    📤 Export (DB &rarr; Config File)
                </button>
            </div>
            <small style="color:var(--text-muted); font-size:0.8em;">
                Import loads settings from <code>config.yaml</code> into the DB. Export saves DB settings back to file.
            </small>
        `;
        container.appendChild(syncCard);

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

                if (field.schema.type === 'template') {
                    // Template Builder UI
                    formGroup.appendChild(label);
                    const builder = appleMusic.renderTemplateBuilder(
                        field.key,
                        field.value,
                        appleMusic.templateVariables[field.key] || []
                    );
                    formGroup.appendChild(builder);

                } else if (field.schema.type === 'bool') {
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

    reloadConfig: async () => {
        // Legacy Reload (Same as Import basically, but specific endpoint maybe?)
        // The backend 'reload_config_from_disk' calls '_sync_from_yaml_to_db'
        // So this is redundant with syncImport, but we'll keep it as "Reload UI" or just alias it.
        appleMusic.syncImport();
    },

    syncImport: async () => {
        if(!confirm("Import settings from config.yaml?\nThis will overwrite the current Database values.")) return;

        try {
            const res = await fetch('/api/apps/apple-music/sync/import', { method: 'POST' });
            const json = await res.json();

            if (json.error) showToast("Import Failed: " + json.error, "error");
            else {
                showToast("Import Success: " + json.message, "success");
                appleMusic.loadConfig(); // Refresh UI
            }
        } catch(e) { showToast("Error: " + e, "error"); }
    },

    syncExport: async () => {
        if(!confirm("Export settings to config.yaml?\nThis will overwrite the file with Database values.")) return;

        try {
            const res = await fetch('/api/apps/apple-music/sync/export', { method: 'POST' });
            const json = await res.json();

            if (json.error) showToast("Export Failed: " + json.error, "error");
            else showToast("Export Success: " + json.message, "success");
        } catch(e) { showToast("Error: " + e, "error"); }
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

    // --- DOWNLOADER LOGIC ---

    startDirectDownload: async () => {
        const url = document.getElementById('am-url-input').value.trim();
        if (!url) { showToast("Please enter URL", "error"); return; }

        // 1. Check Status (Mutual Exclusion)
        try {
            const statusRes = await fetch('/api/apps/apple-music/downloader/status');
            const status = await statusRes.json();

            if (status.running) {
                if (status.queue_active) {
                    if (!confirm("The Queue is currently running.\nStop it to start this download immediately?")) return;

                    // Stop Queue
                    await appleMusic.stopQueue();
                    showToast("Stopping queue... please wait.", "warning");

                    // We should wait until it actually stops, but for now simple delay or just proceeding
                    // (the backend might reject if process is still running, but stop request sets flag)
                    // Ideally we poll until running=false.
                    await new Promise(r => setTimeout(r, 1000));
                } else {
                    showToast("A direct download is already running!", "error");
                    return;
                }
            }
        } catch(e) { console.error("Status check failed", e); }

        const args = appleMusic.getDownloadArgs();

        if(!confirm(`Start Direct Download?\n${url}`)) return;

        try {
            const res = await fetch('/api/apps/apple-music/download', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ url: url, args: args })
            });
            const data = await res.json();

            if (data.status === 'queued') {
                showToast("Download Started!", "success");
                document.getElementById('am-url-input').value = '';
                appleMusic.startConsolePoll();
            } else {
                showToast("Error: " + data.error, "error");
            }
        } catch (e) {
            showToast("Request Failed: " + e, "error");
        }
    },

    getDownloadArgs: () => {
        const args = {};
        if (document.getElementById('am-opt-atmos').checked) args.atmos = true;
        if (document.getElementById('am-opt-aac').checked) args.aac = true;
        if (document.getElementById('am-opt-song').checked) args.song = true;
        if (document.getElementById('am-opt-all-album').checked) args['all-album'] = true;

        if (document.getElementById('am-opt-select').checked) {
            const sel = document.getElementById('am-opt-select-val').value.trim();
            if (sel) args.select = sel;
        }

        if (document.getElementById('am-opt-mv').checked) {
            const max = document.getElementById('am-opt-mv-max').value;
            if(max) args['mv-max'] = parseInt(max);
        }
        return args;
    },

    handleFetch: async () => {
        // Renamed/Aliased to Add to Queue
        const url = document.getElementById('am-url-input').value.trim();
        if (!url) { showToast("Please enter URL", "error"); return; }

        const args = appleMusic.getDownloadArgs();

        try {
            const res = await fetch('/api/apps/apple-music/queue/add', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ url: url, args: args })
            });
            const json = await res.json();

            if(json.status === 'success') {
                showToast("Added to Queue", "success");
                document.getElementById('am-url-input').value = '';
                // Optional: Switch to Queue Tab?
                // appleMusic.switchTab('queue');
            } else {
                showToast("Queue Failed: " + json.error, "error");
            }
        } catch(e) {
            showToast("Error: " + e, "error");
        }
    },

    // --- QUEUE & HISTORY LOGIC ---
    queuePollInterval: null,

    loadQueue: async () => {
        try {
            const res = await fetch('/api/apps/apple-music/queue');
            const allItems = await res.json();

            // Split into Active and History
            const activeItems = allItems.filter(i => i.status === 'pending' || i.status === 'processing');
            const historyItems = allItems.filter(i => i.status === 'completed' || i.status === 'failed');

            // 1. Render Active Queue
            const qContainer = document.getElementById('am-queue-table-body');
            if(qContainer) {
                qContainer.innerHTML = '';
                if(activeItems.length === 0) {
                    qContainer.innerHTML = '<tr><td colspan="5" style="text-align:center; padding:20px; color:var(--text-muted);">Queue is empty</td></tr>';
                } else {
                    activeItems.forEach(item => qContainer.appendChild(appleMusic.renderQueueRow(item, false)));
                }
            }

            // 2. Render History
            const hContainer = document.getElementById('am-history-table-body');
            if(hContainer) {
                hContainer.innerHTML = '';
                if(historyItems.length === 0) {
                    hContainer.innerHTML = '<tr><td colspan="6" style="text-align:center; padding:20px; color:var(--text-muted);">History is empty</td></tr>';
                } else {
                    historyItems.reverse().forEach(item => hContainer.appendChild(appleMusic.renderQueueRow(item, true)));
                }
            }

        } catch(e) { console.error("Queue load error", e); }
    },

    renderQueueRow: (item, isHistory) => {
        const tr = document.createElement('tr');

        // Parse Args
        let argStr = '';
        try {
            const a = JSON.parse(item.args);
            argStr = Object.keys(a).map(k => k + (a[k]===true?'':`=${a[k]}`)).join(', ');
        } catch(e) {}

        // Status Color
        let statusColor = 'gray';
        if(item.status === 'processing') statusColor = '#7aa2f7';
        if(item.status === 'completed') statusColor = '#9ece6a';
        if(item.status === 'failed') statusColor = '#f7768e';

        // History specific details
        let details = '';
        if (isHistory) {
            if (item.status === 'failed') details = `<span style="color:#f7768e; font-size:0.8em;">${item.error || 'Unknown error'}</span>`;
            else details = `<span style="color:var(--text-muted); font-size:0.8em;">${item.created_at || ''}</span>`;
        }

        // Actions
        let actions = '';
        if (isHistory) {
            // Retry & Delete
            actions = `
                <button class="icon-btn" onclick="appleMusic.retryItem(${item.id})" title="Retry" style="color:var(--accent-color);">🔄</button>
                <button class="icon-btn danger" onclick="appleMusic.deleteQueueItem(${item.id})" title="Delete">✖</button>
            `;
        } else {
            // Active: Delete if pending
            if (item.status === 'pending') {
                actions = `<button class="icon-btn danger" onclick="appleMusic.deleteQueueItem(${item.id})">✖</button>`;
            }
        }

        tr.innerHTML = `
            <td style="padding:10px; color:#565f89;">#${item.id}</td>
            <td style="padding:10px; color:#c0caf5; font-family:monospace; max-width:300px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">${item.url}</td>
            <td style="padding:10px; font-size:0.85em; color:#bb9af7;">${argStr}</td>
            <td style="padding:10px;"><span class="badge" style="background:${statusColor}">${item.status.toUpperCase()}</span></td>
            ${isHistory ? `<td style="padding:10px;">${details}</td>` : ''}
            <td style="padding:10px; text-align:right;">${actions}</td>
        `;
        return tr;
    },

    deleteQueueItem: async (id) => {
        if(!confirm("Remove item from database?")) return;
        await fetch(`/api/apps/apple-music/queue/${id}`, {method: 'DELETE'});
        appleMusic.loadQueue();
    },

    retryItem: async (id) => {
        if(!confirm("Retry this download?\nIt will be moved back to the Pending Queue.")) return;
        try {
            const res = await fetch(`/api/apps/apple-music/queue/${id}/retry`, {method: 'POST'});
            const json = await res.json();
            if(json.status === 'success') {
                showToast("Item moved to Queue", "success");
                appleMusic.loadQueue();
            } else {
                showToast("Retry failed", "error");
            }
        } catch(e) {
            showToast("Error: " + e, "error");
        }
    },

    clearHistory: async () => {
        if(!confirm("Clear all Completed and Failed items from history?")) return;
        try {
            const res = await fetch('/api/apps/apple-music/queue/history', {method: 'DELETE'});
            const json = await res.json();
            if(json.status === 'success') {
                showToast("History Cleared", "success");
                appleMusic.loadQueue();
            }
        } catch(e) {
            showToast("Error: " + e, "error");
        }
    },

    startQueue: async () => {
        // Mutual Exclusion Check
        try {
            const statusRes = await fetch('/api/apps/apple-music/downloader/status');
            const status = await statusRes.json();
            if (status.running && !status.queue_active) {
                showToast("A direct download is currently running.\nPlease wait for it to finish.", "error");
                return;
            }
        } catch(e) {}

        const res = await fetch('/api/apps/apple-music/queue/start', {method: 'POST'});
        const json = await res.json();
        if(json.status === 'started') showToast("Queue Processor Started", "success");
        else showToast("Status: " + json.status, "info");
    },

    stopQueue: async () => {
        const res = await fetch('/api/apps/apple-music/queue/stop', {method: 'POST'});
        const json = await res.json();
        showToast("Queue stopping after current job...", "warning");
    },

    // --- CONSOLE LOGIC ---
    downloaderPollInterval: null,

    startConsolePoll: () => {
        if(appleMusic.downloaderPollInterval) clearInterval(appleMusic.downloaderPollInterval);
        appleMusic.pollConsole(); // Immediate
        appleMusic.downloaderPollInterval = setInterval(appleMusic.pollConsole, 1000);
    },

    pollConsole: async () => {
        try {
            const res = await fetch('/api/apps/apple-music/downloader/status');
            const data = await res.json();

            const consoleEl = document.getElementById('am-dl-console');
            if(!consoleEl) return;

            // Only update if logs changed to avoid flicker/perf issues?
            // Simple approach: join and replace
            const text = data.logs.join('\n');
            if (consoleEl.innerText !== text) {
                consoleEl.innerText = text;
                consoleEl.scrollTop = consoleEl.scrollHeight;
            }

            if (!data.running && appleMusic.downloaderPollInterval) {
                // Stop polling if finished? Or keep polling for a bit?
                // User might want to see the last message.
                // Let's keep polling slowly or stop after 10s of inactivity?
                // Ideally, keep polling so user sees "Download Complete" message.
                // We'll leave it running for now as long as the tab is open.
            }
        } catch(e) { console.error("Console poll failed", e); }
    },

    // Legacy mock functions removed/stubbed
    mockFetchSuccess: () => {},
    renderResult: () => {},
    addToQueue: () => {}
};

// Expose globally
window.appleMusic = appleMusic;
window.openAppleMusicApp = appleMusic.open;
