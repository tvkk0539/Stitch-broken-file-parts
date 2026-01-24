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

    stepDiv.innerHTML = `
        <div style="display:flex; justify-content:space-between; margin-bottom:5px;">
            <select class="wf-step-type" style="width:auto;">
                <option value="pack">Pack (Archive)</option>
                <option value="github_publish">GitHub Publish</option>
                <option value="catalog_add">Add to Catalog</option>
            </select>
            <button class="danger" onclick="this.parentElement.parentElement.remove()" style="padding:2px 8px; font-size:0.8em; flex:0;">X</button>
        </div>
        <div class="wf-step-config">
            <!-- Config fields based on type -->
            <input type="text" class="wf-conf-1" placeholder="Config 1 (e.g. Split Size)">
            <input type="text" class="wf-conf-2" placeholder="Config 2 (e.g. Repo)">
        </div>
    `;
    container.appendChild(stepDiv);
}

async function saveWorkflow() {
    const name = document.getElementById('wf-name').value;
    const stepDivs = document.querySelectorAll('.wf-step');
    const steps = [];

    stepDivs.forEach(div => {
        const type = div.querySelector('.wf-step-type').value;
        const conf1 = div.querySelector('.wf-conf-1').value;
        const conf2 = div.querySelector('.wf-conf-2').value;

        let config = {};
        if(type === 'pack') {
            config = { split: conf1 || '1024M', naming: 'part001', format: 'rar' };
        } else if(type === 'github_publish') {
            config = { repo: conf1, tag_template: conf2 };
        } else if(type === 'catalog_add') {
            config = { category: conf1, priority: 1 };
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
