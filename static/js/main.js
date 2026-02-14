// --- Globals ---
let currentPath = '';
let selectedPaths = [];
let expandedJobIds = new Set();
let browserMode = 'local';
let currentRemote = '';
let mcAction = 'move';
let mcCurrentBrowserPath = '';
let mcContext = 'local';

// Log Tabs State
let activeLogTab = 'system'; // 'system' or job_id
let logEventSource = null;
let currentRunningJobIds = []; // Track to add/remove tabs

// --- View Router ---
function switchView(viewName) {
    // Hide all views
    document.querySelectorAll('.view-section').forEach(el => el.classList.remove('active'));
    document.getElementById(`view-${viewName}`).classList.add('active');

    // Update Sidebar
    document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));

    // Find item by data-view attribute for robustness
    let targetView = viewName;
    if(viewName === 'gh-app' || viewName === 'apple-music' || viewName === 'media-tool') targetView = 'apps';

    const activeNav = document.querySelector(`.nav-item[data-view="${targetView}"]`);
    if(activeNav) activeNav.classList.add('active');

    if(viewName === 'settings' && typeof loadSettings === 'function') {
        loadSettings();
    }
}

// --- Common Helpers ---
function showToast(msg, type='info') {
    const t = document.createElement('div'); t.className=`toast ${type}`; t.textContent=msg;
    document.getElementById('toast-container').appendChild(t);
    setTimeout(()=>t.classList.add('show'),10);
    setTimeout(()=>{t.classList.remove('show');setTimeout(()=>t.remove(),300)},4000);
}

function formatBytes(bytes) {
    if(bytes===0) return '0 B';
    if(!bytes || isNaN(bytes) || bytes < 0) return '-';
    const sizes=['B','KB','MB','GB','TB'];
    const i=Math.floor(Math.log(bytes)/Math.log(1024));
    return parseFloat((bytes/Math.pow(1024,i)).toFixed(2))+' '+sizes[i];
}

// --- Modal Closers ---
document.querySelectorAll('.modal .danger, .modal .secondary').forEach(b => {
    if(b.id.startsWith('cancel-') || b.id.startsWith('close-')) {
        b.onclick = () => b.closest('.modal').style.display='none';
    }
});
window.onclick = (e) => { if(e.target.classList.contains('modal')) e.target.style.display='none'; };

// --- Stats Poller ---
function startStatsPoller() {
    fetchStats();
    setInterval(fetchStats, 5000);
}
async function fetchStats() {
    try {
        const res = await fetch('/api/system/stats');
        const data = await res.json();
        document.getElementById('stat-disk-bar').style.width = data.disk.percent + '%';
        document.getElementById('stat-disk-text').textContent = data.disk.free_gb + 'GB Free';
        document.getElementById('stat-ram-bar').style.width = data.ram + '%';
        document.getElementById('stat-ram-text').textContent = data.ram + '%';
        document.getElementById('stat-cpu-text').textContent = data.cpu + '%';
    } catch(e) {}
}

// --- Logs & Tabs ---

function initLogs() {
    // Inject Tab Structure if not present (replacing simple header)
    const logsView = document.getElementById('view-logs');
    if (!document.getElementById('log-tabs-container')) {
        logsView.innerHTML = `
            <div style="display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid var(--border-color); padding-bottom:10px; margin-bottom:10px;">
                <div id="log-tabs-container" style="display:flex; gap:10px; overflow-x:auto; flex:1;">
                    <button class="log-tab active" data-id="system" onclick="switchLogTab('system')">System</button>
                </div>
                <button class="secondary" onclick="clearLogs()" style="flex-shrink:0; margin-left:10px;">Clear Logs</button>
            </div>
            <div id="console">Waiting for logs...</div>
        `;
    }

    // Connect to System Log by default
    connectLogStream('system');
}

function switchLogTab(id) {
    activeLogTab = id;

    // UI Update
    document.querySelectorAll('.log-tab').forEach(b => {
        if(b.dataset.id === id) b.classList.add('active');
        else b.classList.remove('active');
    });

    // Reconnect Stream
    connectLogStream(id);
}

function connectLogStream(id) {
    if(logEventSource) {
        logEventSource.close();
    }

    const consoleDiv = document.getElementById('console');
    consoleDiv.innerHTML = ''; // Clear current view

    const url = id === 'system' ? '/api/logs' : `/api/logs/${id}`;

    logEventSource = new EventSource(url);

    logEventSource.onmessage = function(event) {
        const newLog = document.createElement('div');
        newLog.textContent = event.data;
        consoleDiv.appendChild(newLog);
        consoleDiv.scrollTop = consoleDiv.scrollHeight;
    };

    logEventSource.onerror = function() {
        // If job finishes, stream might close.
        // Optional: show "Stream ended"
    };
}

// Called by queue.js polling loop
function updateLogTabs(data) {
    const container = document.getElementById('log-tabs-container');
    if(!container) return; // logs view not ready

    const running = data.running || [];
    const runningIds = new Set(running.map(j => j.id));

    // 1. Add new tabs
    running.forEach(job => {
        if (!currentRunningJobIds.includes(job.id)) {
            const btn = document.createElement('button');
            btn.className = 'log-tab';
            btn.dataset.id = job.id;
            btn.textContent = getShortName(job.name);
            btn.title = job.name;
            btn.onclick = () => switchLogTab(job.id);
            container.appendChild(btn);
            currentRunningJobIds.push(job.id);
        }
    });

    // 2. Remove tabs for finished jobs?
    // User might want to see logs of finished jobs.
    // Strategy: Keep them until "Clear History" or manual close?
    // To match user request "shows only one job... until finishes", we probably WANT to see finished ones.
    // BUT: if we keep them forever, tabs will overflow.
    // Compromise: Keep them in the list, but maybe mark them as (Done).
    // For now, let's NOT remove them automatically so user can inspect.
    // We will just update their text to indicate done?

    // Actually, simply remove them from "running" list doesn't mean we must remove tab immediately.
    // But if we remove tab, user loses the specific log context.
    // Let's remove tab ONLY if it's NOT active. If active, keep it until user switches away?
    // Or just keep them for a bit.
    // Simple approach: Only show tabs for RUNNING jobs. If job finishes, it disappears from tabs?
    // User complaint was: "others won't show until first job finishes".
    // So the goal is to see concurrent running jobs.
    // I will REMOVE tabs for finished jobs to keep UI clean, UNLESS it's the active tab.

    const tabs = Array.from(container.children);
    tabs.forEach(tab => {
        const tid = tab.dataset.id;
        if(tid === 'system') return;

        if (!runningIds.has(tid)) {
             // Job finished
             if(activeLogTab === tid) {
                 tab.textContent = `(Done) ${tab.textContent.replace('(Done) ', '')}`;
                 tab.style.opacity = '0.7';
             } else {
                 // Remove inactive, finished job tabs
                 tab.remove();
                 currentRunningJobIds = currentRunningJobIds.filter(id => id !== tid);
             }
        }
    });
}

function getShortName(name) {
    // "Download 5 items from GDrive" -> "Download..."
    // "Pack my_movie" -> "Pack..."
    if(name.length > 15) return name.substring(0, 15) + '...';
    return name;
}

async function clearLogs() {
    if(confirm("Clear all logs and job history?")) {
        try {
            const res = await fetch('/api/jobs/history/clear', {method:'POST'});
            if (!res.ok) throw new Error("Failed to clear");
            document.getElementById('console').innerHTML = '';
            showToast("Logs Cleared", "success");
        } catch(e) {
            showToast("Failed to clear logs", "error");
        }
    }
}

function openAppleMusicApp() {
    switchView('apple-music');
}

function openMediaToolApp() {
    switchView('media-tool');
    if(window.mediaTool && window.mediaTool.init) window.mediaTool.init();
}

// Initialize core components on load
document.addEventListener('DOMContentLoaded', () => {
    initLogs();
    startStatsPoller();
    if(window.catalog) window.catalog.init();
    if(window.initAutomation) window.initAutomation();
    if(window.stealth) window.stealth.init();
    if(window.mediaTool) window.mediaTool.init();
});
