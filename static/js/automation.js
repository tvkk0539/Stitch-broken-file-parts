// Automation Logic

let workflows = [];

function initAutomation() {
    loadWorkflows();
}

async function loadWorkflows() {
    try {
        const res = await fetch('/api/automation/workflows');
        workflows = await res.json();
        renderWorkflows();
    } catch(e) {
        console.error("Failed to load workflows", e);
    }
}

function renderWorkflows() {
    const container = document.getElementById('workflow-list');
    if(!container) return;
    container.innerHTML = '';

    workflows.forEach(wf => {
        const card = document.createElement('div');
        card.className = 'app-card';
        card.style.height = 'auto';
        card.innerHTML = `
            <div style="font-size:2em; margin-bottom:10px;">🤖</div>
            <div class="app-name">${wf.name}</div>
            <div class="app-desc">${wf.steps.length} Steps</div>
            <div style="margin-top:15px; display:flex; gap:5px;">
                <button class="secondary" onclick="runWorkflow('${wf.id}')">Run</button>
                <button class="danger" onclick="deleteWorkflow('${wf.id}')" style="flex:0;">🗑️</button>
            </div>
        `;
        container.appendChild(card);
    });
}

function openWorkflowModal() {
    document.getElementById('workflow-modal').style.display = 'block';
    document.getElementById('wf-name').value = '';
    document.getElementById('wf-steps-container').innerHTML = '';
}

function addWorkflowStepUI() {
    const container = document.getElementById('wf-steps-container');
    const stepDiv = document.createElement('div');
    stepDiv.className = 'wf-step';
    stepDiv.style.background = '#13141c';
    stepDiv.style.padding = '10px';
    stepDiv.style.marginBottom = '10px';
    stepDiv.style.border = '1px solid var(--border-color)';

    // We only support the specific "Gh Uploads to Index" pipeline for now
    // So we pre-fill or simplify. But flexibility is better.
    // Let's allow selecting "Analyze Source" which is crucial.

    stepDiv.innerHTML = `
        <div style="display:flex; justify-content:space-between; margin-bottom:5px;">
            <select class="wf-step-type" style="width:auto;" onchange="updateStepConfigUI(this)">
                <option value="analyze_source">1. Analyze Source (Pre-Index)</option>
                <option value="pack">2. Pack (Archive)</option>
                <option value="github_publish">3. GitHub Publish</option>
                <option value="catalog_add">4. Add to Catalog</option>
            </select>
            <button class="danger" onclick="this.parentElement.parentElement.remove()" style="padding:2px 8px; font-size:0.8em; flex:0;">X</button>
        </div>
        <div class="wf-step-config" style="display:flex; gap:5px;">
            <input type="text" class="wf-conf-1" placeholder="Config 1">
            <input type="text" class="wf-conf-2" placeholder="Config 2">
            <input type="text" class="wf-conf-3" placeholder="Config 3">
        </div>
        <div class="wf-step-desc" style="font-size:0.8em; color:gray; margin-top:5px;">
            Select a step type to see details.
        </div>
    `;
    container.appendChild(stepDiv);
    // Trigger update to show correct placeholders
    updateStepConfigUI(stepDiv.querySelector('.wf-step-type'));
}

function updateStepConfigUI(select) {
    const type = select.value;
    const container = select.closest('.wf-step');
    const c1 = container.querySelector('.wf-conf-1');
    const c2 = container.querySelector('.wf-conf-2');
    const c3 = container.querySelector('.wf-conf-3');
    const desc = container.querySelector('.wf-step-desc');

    c1.style.display = 'block'; c2.style.display = 'block'; c3.style.display = 'block';

    if (type === 'analyze_source') {
        c1.style.display = 'none'; c2.style.display = 'none'; c3.style.display = 'none';
        desc.textContent = "Scans folder, builds file tree, calculates original sizes.";
    } else if (type === 'pack') {
        c1.placeholder = "Split (e.g. 1024M)";
        c2.placeholder = "Naming (part001)";
        c3.style.display = 'none';
        desc.textContent = "Creates split RAR archives with Recovery Record.";
    } else if (type === 'github_publish') {
        c1.placeholder = "Repo (user/repo)";
        c2.placeholder = "Account ID (See GitHub App)";
        c3.placeholder = "Tag (v{date}_{name})";
        desc.textContent = "Uploads archives to Release. Embeds Analysis Tree in Body.";
    } else if (type === 'catalog_add') {
        c1.placeholder = "Category (Movies/4K)";
        c2.placeholder = "Priority (2=High, 1=Normal)";
        c3.style.display = 'none';
        desc.textContent = "Adds to local index with download links and syncs to bridge.";
    }
}

async function saveWorkflow() {
    const name = document.getElementById('wf-name').value;
    const stepDivs = document.querySelectorAll('.wf-step');
    const steps = [];

    stepDivs.forEach(div => {
        const type = div.querySelector('.wf-step-type').value;
        const conf1 = div.querySelector('.wf-conf-1').value;
        const conf2 = div.querySelector('.wf-conf-2').value;
        const conf3 = div.querySelector('.wf-conf-3').value;

        let config = {};
        if(type === 'pack') {
            config = { split: conf1 || '1024M', naming: conf2 || 'part001', format: 'rar', recovery: true };
        } else if(type === 'github_publish') {
            config = { repo: conf1, account_id: conf2, tag_template: conf3 || 'v{date}_{name}' };
        } else if(type === 'catalog_add') {
            config = { category: conf1 || 'General', priority: parseInt(conf2) || 1 };
        }

        steps.push({ type: type, config: config });
    });

    if(!name || steps.length === 0) {
        alert("Name and at least one step required.");
        return;
    }

    try {
        await fetch('/api/automation/workflows', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ name: name, steps: steps })
        });
        document.getElementById('workflow-modal').style.display = 'none';
        loadWorkflows();
        showToast("Workflow Saved!");
    } catch(e) {
        alert("Save failed: " + e);
    }
}

async function runWorkflow(id) {
    // For demo, we run on selected files
    if(selectedPaths.length === 0) {
        alert("Please select files in the Files tab first!");
        switchView('files');
        return;
    }

    try {
        const res = await fetch(`/api/automation/run/${id}`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ files: selectedPaths })
        });
        const d = await res.json();
        if(d.status === 'queued') {
            showToast("Workflow Started!");
            switchView('queue');
        } else {
            alert("Error: " + d.error);
        }
    } catch(e) {
        alert("Run failed: " + e);
    }
}

async function deleteWorkflow(id) {
    if(!confirm("Delete this workflow?")) return;
    await fetch(`/api/automation/workflows/${id}`, { method: 'DELETE' });
    loadWorkflows();
}

// Global Exposure
window.initAutomation = initAutomation;
