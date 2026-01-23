const jobQueueContainer = document.getElementById('job-queue-container');
const activeJobText = document.getElementById('active-job-text');

function startJobPoller() {
    fetchJobs();
    setInterval(fetchJobs, 2000);
}

async function fetchJobs() {
    try {
        const res = await fetch('/api/jobs');
        const data = await res.json();
        renderJobQueue(data);
        updateActiveJobWidget(data);

        // Notify main.js to update logs tabs if function exists
        if(typeof updateLogTabs === 'function') {
            updateLogTabs(data);
        }
    } catch (e) {}
}

function updateActiveJobWidget(data) {
    const runningCount = data.running ? data.running.length : 0;
    const pendingCount = data.pending ? data.pending.length : 0;

    if (runningCount > 0) {
        if (runningCount === 1) {
            activeJobText.textContent = `Running: ${data.running[0].name}`;
        } else {
            activeJobText.textContent = `${runningCount} Jobs Running`;
        }
        activeJobText.style.color = 'var(--accent-color)';
    } else if (pendingCount > 0) {
        activeJobText.textContent = `${pendingCount} Jobs Queued`;
        activeJobText.style.color = 'var(--text-muted)';
    } else {
        activeJobText.textContent = "Idle";
        activeJobText.style.color = 'var(--text-muted)';
    }
}

function renderJobQueue(data) {
    jobQueueContainer.innerHTML = '';

    if (data.running && data.running.length > 0) {
        jobQueueContainer.innerHTML += '<h3>Running</h3>';
        data.running.forEach(j => jobQueueContainer.appendChild(createJobCard(j, 'running')));
    }
    if (data.pending && data.pending.length > 0) {
        jobQueueContainer.innerHTML += '<h3>Pending</h3>';
        data.pending.forEach(j => jobQueueContainer.appendChild(createJobCard(j, 'queued')));
    }
    if (data.history && data.history.length > 0) {
        jobQueueContainer.innerHTML += `<div style="display:flex;justify-content:space-between;align-items:center;margin-top:20px;border-bottom:1px solid #414868;padding-bottom:5px;"><h3>History</h3><button class="icon-btn" onclick="clearHistory()">Clear</button></div>`;
        data.history.forEach(j => jobQueueContainer.appendChild(createJobCard(j, j.status || 'completed')));
    }
    if ((!data.running || data.running.length === 0) && (!data.pending || data.pending.length === 0) && (!data.history || data.history.length === 0)) {
        jobQueueContainer.innerHTML = '<div style="text-align:center;color:var(--text-muted);margin-top:50px;">Queue is empty</div>';
    }
}

function createJobCard(job, status) {
    const card = document.createElement('div');
    card.className = `job-card ${status}`;

    let statusText = status.toUpperCase();
    if(status==='running') statusText = 'RUNNING...';
    if(status==='cancelling') statusText = 'CANCELLING...';

    card.innerHTML = `
        <div class="job-header">
            <div>
                <span class="job-name">${job.name}</span>
                <span class="job-meta">${statusText}</span>
            </div>
            ${(status==='running'||status==='queued') ? `<button class="btn-cancel" onclick="cancelJob('${job.id}', event)">Cancel</button>` : ''}
        </div>
        <div class="job-details" id="details-${job.id}">${renderJobDetails(job.details)}</div>
    `;

    if(expandedJobIds.has(job.id)) card.querySelector('.job-details').classList.add('expanded');

    card.onclick = (e) => {
        if(e.target.tagName === 'BUTTON') return;
        const det = card.querySelector('.job-details');
        if(det.classList.contains('expanded')) {
            det.classList.remove('expanded');
            expandedJobIds.delete(job.id);
        } else {
            det.classList.add('expanded');
            expandedJobIds.add(job.id);
        }
    };
    return card;
}

function renderJobDetails(details) {
    if(!details) return 'No details.';
    let html = '';
    // Render basic keys
    for(const [k,v] of Object.entries(details)) {
        if(k==='targets') continue;
        html += `<div><strong>${k}:</strong> ${v}</div>`;
    }
    // Render targets
    if(details.targets && Array.isArray(details.targets)) {
        html += `<div style="margin-top:5px;"><strong>Files:</strong><ul style="margin:0;padding-left:20px;max-height:100px;overflow-y:auto;">${details.targets.map(t=>`<li>${t}</li>`).join('')}</ul></div>`;
    }
    return html || 'No details.';
}

async function cancelJob(id, e) {
    if(e) e.stopPropagation();
    if(confirm("Cancel Job?")) {
        await fetch(`/api/jobs/cancel/${id}`, {method:'POST'});
        fetchJobs();
    }
}

async function clearHistory() {
    if(confirm("Clear History?")) {
        await fetch('/api/jobs/history/clear', {method:'POST'});
        fetchJobs();
    }
}

// Init
document.addEventListener('DOMContentLoaded', () => {
    startJobPoller();
});
