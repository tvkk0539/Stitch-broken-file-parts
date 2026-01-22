// --- Globals ---
let currentPath = '';
let selectedPaths = [];
let expandedJobIds = new Set();
let browserMode = 'local';
let currentRemote = '';
let mcAction = 'move';
let mcCurrentBrowserPath = '';
let mcContext = 'local';

// --- View Router ---
function switchView(viewName) {
    // Hide all views
    document.querySelectorAll('.view-section').forEach(el => el.classList.remove('active'));
    document.getElementById(`view-${viewName}`).classList.add('active');

    // Update Sidebar
    document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));

    // Find item by data-view attribute for robustness
    let targetView = viewName;
    if(viewName === 'gh-app') targetView = 'apps';

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

// --- Logs ---
function initLogs() {
    const consoleDiv = document.getElementById('console');
    const evtSource = new EventSource("/api/logs");
    evtSource.onmessage = function(event) {
        const newLog = document.createElement('div');
        newLog.textContent = event.data;
        consoleDiv.appendChild(newLog);
        consoleDiv.scrollTop = consoleDiv.scrollHeight;
    };
}

// Initialize core components on load
document.addEventListener('DOMContentLoaded', () => {
    initLogs();
    startStatsPoller();
});
