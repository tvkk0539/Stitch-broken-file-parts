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

    // --- REAL DOWNLOADER LOGIC ---

    handleFetch: async () => {
        const url = document.getElementById('am-url-input').value;
        if (!url) {
            showToast("Please enter an Apple Music URL", "error");
            return;
        }

        const args = {};

        // Gather Options
        if (document.getElementById('am-opt-atmos').checked) args.atmos = true;
        if (document.getElementById('am-opt-aac').checked) args.aac = true;
        if (document.getElementById('am-opt-song').checked) args.song = true;
        if (document.getElementById('am-opt-select').checked) {
            const sel = document.getElementById('am-opt-select-val').value.trim();
            if (sel) args.select = sel;
        }

        if(!confirm(`Start download for:\n${url}`)) return;

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

                // Start Polling Console
                appleMusic.startConsolePoll();
            } else {
                showToast("Error: " + data.error, "error");
            }
        } catch (e) {
            showToast("Request Failed: " + e, "error");
        }
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
