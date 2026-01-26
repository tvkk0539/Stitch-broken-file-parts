// Apple Music Downloader App Logic

const appleMusic = {
    state: {
        currentAlbum: null,
        queue: []
    },

    init: () => {
        // Any initialization if needed on page load
        console.log("Apple Music App Initialized");
    },

    open: () => {
        switchView('apple-music');
        appleMusic.switchTab('down'); // Default tab
    },

    switchTab: (tab) => {
        // Tabs: 'down', 'setup'
        document.querySelectorAll('.browser-tab').forEach(b => b.classList.remove('active'));
        document.getElementById(`am-tab-${tab}`).classList.add('active');

        document.getElementById('am-view-down').style.display = 'none';
        document.getElementById('am-view-setup').style.display = 'none';

        document.getElementById(`am-view-${tab}`).style.display = 'block';
    },

    handleImportRepo: async () => {
        const url = document.getElementById('am-setup-url').value.trim();
        if (!url) {
            showToast("Please enter a Repository URL", "error");
            return;
        }

        // Validate basic git url structure
        if (!url.startsWith('http') || !url.endsWith('.git')) {
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

    // UI Actions
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
