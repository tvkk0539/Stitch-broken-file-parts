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
                <option value="enrich_metadata">3b. Enrich Metadata (Text/URL)</option>
                <option value="catalog_add">4. Add to Catalog</option>
            </select>
            <button class="danger" onclick="this.parentElement.parentElement.remove()" style="padding:2px 8px; font-size:0.8em; flex:0;">X</button>
        </div>
        <div class="wf-step-config" style="display:flex; gap:5px; flex-wrap:wrap;">
            <input type="text" class="wf-conf-1" placeholder="Config 1" style="flex:1;">
            <input type="text" class="wf-conf-2" placeholder="Config 2" style="flex:1;">
            <input type="text" class="wf-conf-3" placeholder="Config 3" style="flex:1;">
            <textarea class="wf-conf-long" placeholder="Description/Content" style="display:none; width:100%; height:100px; margin-top:5px; background:#1a1b26; border:1px solid var(--border-color); color:#c0caf5; padding:10px;"></textarea>
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
    const cLong = container.querySelector('.wf-conf-long');
    const desc = container.querySelector('.wf-step-desc');

    c1.style.display = 'block'; c2.style.display = 'block'; c3.style.display = 'block';
    if(cLong) cLong.style.display = 'none';

    // Create Select for Split Size if Pack
    if (type === 'pack' && c1.tagName !== 'SELECT') {
        // Replace Input with Select
        const sel = document.createElement('select');
        sel.className = 'wf-conf-1';
        sel.innerHTML = `
            <option value="100M">100MB</option>
            <option value="500M">500MB</option>
            <option value="1024M" selected>1GB</option>
            <option value="2048M">2GB</option>
            <option value="5120M">5GB</option>
        `;
        c1.replaceWith(sel);
    }

    // Re-query in case we replaced it
    const c1_new = container.querySelector('.wf-conf-1');

    if (type === 'analyze_source') {
        c1_new.style.display = 'none'; c2.style.display = 'none'; c3.style.display = 'none';
        desc.textContent = "Scans folder, builds file tree, calculates original sizes.";
    } else if (type === 'pack') {
        c1_new.style.display = 'block'; // Ensure select is visible
        c2.placeholder = "Naming (part001)";
        c3.placeholder = "Obfuscate Filename? (true/false)";
        c3.style.display = 'block';
        desc.textContent = "Creates split RAR archives. Obfuscation uses Base64 filenames.";
    } else if (type === 'github_publish') {
        // If coming from pack, we need to revert Select to Input?
        if (c1_new.tagName === 'SELECT') {
            const inp = document.createElement('input');
            inp.type = 'text';
            inp.className = 'wf-conf-1';
            c1_new.replaceWith(inp);
        }
        const c1_final = container.querySelector('.wf-conf-1');

        c1_final.placeholder = "Repo (user/repo)";
        c2.placeholder = "Account ID (Number from GitHub App)";
        c3.placeholder = "Obfuscate Title? (true/false)";
        desc.textContent = "Uploads archives. Obfuscation uses Base64 Release Titles.";
    } else if (type === 'enrich_metadata') {
        if (c1_new.tagName === 'SELECT') {
            const inp = document.createElement('input');
            inp.type = 'text';
            inp.className = 'wf-conf-1';
            c1_new.replaceWith(inp);
        }
        const c1_final = container.querySelector('.wf-conf-1');

        c1_final.placeholder = "Reference URL (e.g. IMDB/Wikipedia)";
        c2.style.display = 'none';
        c3.style.display = 'none';
        if(cLong) cLong.style.display = 'block';

        desc.textContent = "Injects custom URL and Long Description into the catalog entry.";

    } else if (type === 'catalog_add') {
        if (c1_new.tagName === 'SELECT') {
            const inp = document.createElement('input');
            inp.type = 'text';
            inp.className = 'wf-conf-1';
            c1_new.replaceWith(inp);
        }
        const c1_final = container.querySelector('.wf-conf-1');

        c1_final.placeholder = "Category (Movies/4K)";
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
        const confLong = div.querySelector('.wf-conf-long') ? div.querySelector('.wf-conf-long').value : '';

        let config = {};
        if(type === 'pack') {
            config = {
                split: conf1 || '1024M',
                naming: conf2 || 'part001',
                format: 'rar',
                recovery: true,
                obfuscate: (conf3 && conf3.toLowerCase() === 'true')
            };
        } else if(type === 'github_publish') {
            config = {
                repo: conf1,
                account_id: conf2,
                obfuscate_title: (conf3 && conf3.toLowerCase() === 'true'),
                tag_template: 'v{date}_{name}'
            };
        } else if(type === 'enrich_metadata') {
            config = {
                reference_url: conf1,
                description: confLong
            };
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
    // 1. Pre-Flight Check: Sync Status
    try {
        const syncRes = await fetch('/api/sync/status');
        const syncData = await syncRes.json();
        if (!syncData.configured) {
            alert("⚠️ Automation Blocked: Data Sync is NOT configured.\n\nPlease go to Settings and link a Private GitHub Repository to ensure your catalog and images are backed up safely.");
            switchView('settings');
            return;
        }
    } catch(e) {
        alert("Failed to check Sync Status: " + e);
        return;
    }

    // 2. Input Validation
    if(selectedPaths.length === 0) {
        alert("Please select a folder in the Files tab first!");
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
window.openWorkflowModal = openWorkflowModal;
window.addWorkflowStepUI = addWorkflowStepUI;
window.saveWorkflow = saveWorkflow;
window.runWorkflow = runWorkflow;
window.deleteWorkflow = deleteWorkflow;
window.updateStepConfigUI = updateStepConfigUI;
