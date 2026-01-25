// Automation Logic

let workflows = [];
let currentEditingId = null;

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
                <button class="secondary" onclick="editWorkflow('${wf.id}')" style="flex:0;">✏️</button>
                <button class="danger" onclick="deleteWorkflow('${wf.id}')" style="flex:0;">🗑️</button>
            </div>
        `;
        container.appendChild(card);
    });
}

function openWorkflowModal() {
    currentEditingId = null; // Reset for new
    document.getElementById('workflow-modal').style.display = 'block';
    document.getElementById('wf-name').value = '';
    document.getElementById('wf-steps-container').innerHTML = '';
    document.querySelector('#workflow-modal h3').textContent = "Create Workflow";

    // Inject Datalist for Categories if not exists
    if(!document.getElementById('cat-datalist')) {
        const dl = document.createElement('datalist');
        dl.id = 'cat-datalist';
        document.body.appendChild(dl);
    }

    // Fetch Categories for Datalist
    fetch('/api/catalog/categories')
        .then(r => r.json())
        .then(cats => {
            const dl = document.getElementById('cat-datalist');
            dl.innerHTML = '';
            cats.forEach(c => {
                const opt = document.createElement('option');
                opt.value = c;
                dl.appendChild(opt);
            });
        }).catch(e => console.error("Failed to load categories for modal", e));

    // Inject Datalist for Tags if not exists
    if(!document.getElementById('tag-datalist')) {
        const dl = document.createElement('datalist');
        dl.id = 'tag-datalist';
        document.body.appendChild(dl);
    }

    // Fetch Tags for Datalist
    fetch('/api/catalog/tags')
        .then(r => r.json())
        .then(tags => {
            const dl = document.getElementById('tag-datalist');
            dl.innerHTML = '';
            tags.forEach(t => {
                const opt = document.createElement('option');
                opt.value = t;
                dl.appendChild(opt);
            });
        }).catch(e => console.error("Failed to load tags for modal", e));

    // Inject Datalist for Repos if not exists
    if(!document.getElementById('gh-repo-list')) {
        const dl = document.createElement('datalist');
        dl.id = 'gh-repo-list';
        document.body.appendChild(dl);
    }

    // Inject Datalist for Accounts if not exists
    if(!document.getElementById('gh-acc-list')) {
        const dl = document.createElement('datalist');
        dl.id = 'gh-acc-list';
        document.body.appendChild(dl);
    }

    // Fetch Accounts for Datalist
    fetch('/api/apps/github/accounts')
        .then(r => r.json())
        .then(accs => {
            const dl = document.getElementById('gh-acc-list');
            dl.innerHTML = '';
            accs.forEach(a => {
                // Option value is ID, but show Name for context
                const opt = document.createElement('option');
                // Standard Datalist: Value is what goes in box.
                // We want ID in box.
                opt.value = a.id;
                opt.label = a.username;
                dl.appendChild(opt);
            });
        }).catch(e => console.error("Failed to load accounts for modal", e));
}

function editWorkflow(id) {
    const wf = workflows.find(w => w.id === id);
    if (!wf) return;

    // Ensure datalist is populated even in edit mode
    openWorkflowModal(); // Re-use init logic (title/value override below)

    currentEditingId = id;
    document.querySelector('#workflow-modal h3').textContent = "Edit Workflow";
    document.getElementById('wf-name').value = wf.name;

    const container = document.getElementById('wf-steps-container');
    container.innerHTML = '';

    wf.steps.forEach(step => {
        // Create UI
        const stepDiv = addWorkflowStepUI(); // Modified to return the div

        // Populate Values
        stepDiv.querySelector('.wf-step-type').value = step.type;
        updateStepConfigUI(stepDiv.querySelector('.wf-step-type'));

        // Populate Config
        const conf = step.config;
        const c1 = stepDiv.querySelector('.wf-conf-1');
        const c2 = stepDiv.querySelector('.wf-conf-2');
        const c3 = stepDiv.querySelector('.wf-conf-3'); // This might be the tag container
        const cLong = stepDiv.querySelector('.wf-conf-long');

        if (step.type === 'pack') {
             c1.value = conf.split || '1024M';
             c2.value = conf.naming || 'part001';
             c3.value = (conf.obfuscate === true || conf.obfuscate === 'true') ? 'true' : 'false';
        } else if (step.type === 'github_publish') {
             c1.value = conf.repo || '';
             c2.value = conf.account_id || '';
             c3.value = (conf.obfuscate_title === true || conf.obfuscate_title === 'true') ? 'true' : 'false';
        } else if (step.type === 'enrich_metadata') {
             c1.value = conf.reference_url || '';
             if(cLong) cLong.value = conf.description || '';
        } else if (step.type === 'catalog_add') {
             c1.value = conf.category || '';
             c2.value = conf.priority || '1';

             // Populate Tag Tokenizer
             // c3 is now a div.tag-container
             // We need to re-initialize the tags inside it
             const tags = (conf.tags || '').split(',').filter(t => t.trim());
             // Clear existing pills except input
             const input = c3.querySelector('.tag-input');
             if(input) {
                 c3.querySelectorAll('.tag-pill').forEach(p => p.remove());
                 tags.forEach(t => addTagPill(c3, input, t.trim()));
                 updateHiddenTagValue(c3);
             }
        }
    });
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
            <select class="wf-step-type" style="width:auto;" onchange="updateStepConfigUI(this)">
                <option value="analyze_source">1. Analyze Source (Pre-Index)</option>
                <option value="pack">2. Pack (Archive)</option>
                <option value="github_publish">3. GitHub Publish</option>
                <option value="enrich_metadata">4. Enrich Metadata (Text/URL)</option>
                <option value="catalog_add">5. Add to Catalog</option>
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
    return stepDiv;
}

// --- Tag Tokenizer Helpers ---

function createTagInput(containerElement, datalistId) {
    // Check if already created
    if (containerElement.classList.contains('tag-container')) return;

    // Convert input to container
    const originalInput = containerElement;

    const wrapper = document.createElement('div');
    wrapper.className = 'tag-container wf-conf-3'; // Keep class for selection

    // Create Hidden Input for Value Storage
    const hiddenInput = document.createElement('input');
    hiddenInput.type = 'hidden';
    hiddenInput.className = 'tag-value';
    wrapper.appendChild(hiddenInput);

    // Create Type Input
    const typeInput = document.createElement('input');
    typeInput.type = 'text';
    typeInput.className = 'tag-input';
    typeInput.setAttribute('list', datalistId);
    typeInput.placeholder = "Type tags + Enter";
    wrapper.appendChild(typeInput);

    // Replace original
    originalInput.replaceWith(wrapper);

    // Event Listeners
    typeInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ',') {
            e.preventDefault();
            const val = typeInput.value.trim().replace(',', '');
            if (val) {
                addTagPill(wrapper, typeInput, val);
                typeInput.value = '';
                updateHiddenTagValue(wrapper);
            }
        } else if (e.key === 'Backspace' && typeInput.value === '') {
            // Remove last tag
            const pills = wrapper.querySelectorAll('.tag-pill');
            if (pills.length > 0) {
                pills[pills.length - 1].remove();
                updateHiddenTagValue(wrapper);
            }
        }
    });

    typeInput.addEventListener('blur', () => {
        const val = typeInput.value.trim().replace(',', '');
        if (val) {
            addTagPill(wrapper, typeInput, val);
            typeInput.value = '';
            updateHiddenTagValue(wrapper);
        }
    });

    return wrapper;
}

function addTagPill(wrapper, inputInfo, text) {
    const pill = document.createElement('div');
    pill.className = 'tag-pill';

    // Create text node
    pill.appendChild(document.createTextNode(text + " "));

    // Create delete span
    const closeBtn = document.createElement('span');
    closeBtn.innerHTML = '×';
    closeBtn.style.cursor = 'pointer';

    // Robust Event Listener
    closeBtn.onclick = (e) => {
        e.stopPropagation();
        pill.remove();
        updateHiddenTagValue(wrapper);
    };

    pill.appendChild(closeBtn);
    wrapper.insertBefore(pill, inputInfo);
}

function updateHiddenTagValue(wrapper) {
    const pills = wrapper.querySelectorAll('.tag-pill');
    // Extract text only (ignore the 'x' button content)
    const values = Array.from(pills).map(p => {
        if (p.firstChild && p.firstChild.nodeType === 3) {
            return p.firstChild.textContent.trim();
        }
        return p.textContent.replace('×', '').trim();
    });
    const hidden = wrapper.querySelector('.tag-value');
    if (hidden) hidden.value = values.join(',');
}

// Global exposure
window.updateHiddenTagValue = updateHiddenTagValue;

// --- Repo Fetch Helper ---
window.fetchReposForAccount = function(input) {
    const accountId = input.value;
    if(!accountId) return;

    fetch(`/api/apps/github/user/repos?account_id=${accountId}`)
        .then(r => r.json())
        .then(repos => {
            const dl = document.getElementById('gh-repo-list');
            if(!dl) return;
            dl.innerHTML = '';
            repos.forEach(r => {
                const opt = document.createElement('option');
                // Assuming repo.name includes owner prefix "user/repo"
                // Wait, API typically returns full_name: "user/repo", name: "repo"
                // Let's check API or just use what we have.
                // list_user_repos returns 'name': item['full_name']
                opt.value = r.name;
                dl.appendChild(opt);
            });
        })
        .catch(e => console.error("Repo fetch failed", e));
};


function updateStepConfigUI(select) {
    const type = select.value;
    const container = select.closest('.wf-step');
    let c1 = container.querySelector('.wf-conf-1');
    let c2 = container.querySelector('.wf-conf-2');
    let c3 = container.querySelector('.wf-conf-3');
    const cLong = container.querySelector('.wf-conf-long');
    const desc = container.querySelector('.wf-step-desc');

    c1.style.display = 'block'; c2.style.display = 'block'; c3.style.display = 'block';
    if(cLong) cLong.style.display = 'none';

    // --- Helpers ---
    const ensureInput = (el, listId=null) => {
        // If it's a TAG CONTAINER (div), revert to input
        if (el.tagName === 'DIV' && el.classList.contains('tag-container')) {
            const inp = document.createElement('input');
            inp.type = 'text';
            inp.className = 'wf-conf-3'; // Restore original class
            el.replaceWith(inp);
            return inp;
        }

        if (el.tagName === 'SELECT' || (el.tagName === 'INPUT' && el.getAttribute('list') !== listId)) {
            const inp = document.createElement('input');
            inp.type = 'text';
            inp.className = el.className;
            if(listId) inp.setAttribute('list', listId);
            else inp.removeAttribute('list');

            // Clean specific event listeners
            inp.onchange = null;

            el.replaceWith(inp);
            return inp;
        }
        return el;
    };

    const ensureSelect = (el, optionsHTML) => {
        // Revert div to select if needed
        if (el.tagName === 'DIV' && el.classList.contains('tag-container')) {
             const sel = document.createElement('select');
             sel.className = 'wf-conf-3';
             sel.innerHTML = optionsHTML;
             // Apply styles
             sel.style.background = '#1a1b26'; sel.style.color = '#c0caf5'; sel.style.border = '1px solid #414868'; sel.style.padding = '5px'; sel.style.flex = '1';
             el.replaceWith(sel);
             return sel;
        }

        const sel = document.createElement('select');
        sel.className = el.className;
        sel.innerHTML = optionsHTML;
        sel.style.background = '#1a1b26';
        sel.style.color = '#c0caf5';
        sel.style.border = '1px solid #414868';
        sel.style.padding = '5px';
        sel.style.flex = '1';
        el.replaceWith(sel);
        return sel;
    };

    if (type === 'analyze_source') {
        c1 = ensureInput(c1); c2 = ensureInput(c2); c3 = ensureInput(c3);
        c1.style.display = 'none'; c2.style.display = 'none'; c3.style.display = 'none';
        desc.textContent = "Scans folder, builds file tree, calculates original sizes.";

    } else if (type === 'pack') {
        // Config 1: Split Size
        const sizeOpts = `
            <option value="1024M" selected>1 GB (Standard)</option>
            <option value="1536M">1.5 GB</option>
            <option value="2048M">2 GB</option>
            <option value="2560M">2.5 GB</option>
            <option value="3072M">3 GB</option>
            <option value="3584M">3.5 GB</option>
            <option value="4096M">4 GB</option>
            <option value="4608M">4.5 GB</option>
            <option value="5120M">5 GB</option>
            <option disabled>--- Small ---</option>
            <option value="200M">200 MB</option>
            <option value="300M">300 MB</option>
            <option value="400M">400 MB</option>
            <option value="500M">500 MB</option>
            <option value="600M">600 MB</option>
            <option value="700M">700 MB</option>
            <option value="800M">800 MB</option>
            <option value="900M">900 MB</option>
            <option disabled>--- Other ---</option>
            <option value="0">No Split</option>
        `;
        c1 = ensureSelect(c1, sizeOpts);

        // Config 2: Naming
        const namingOpts = `
            <option value="part1">part1.rar</option>
            <option value="part01">part01.rar</option>
            <option value="part001" selected>part001.rar (Scene)</option>
        `;
        c2 = ensureSelect(c2, namingOpts);

        // Config 3: Obfuscation
        const obfOpts = `
            <option value="false" selected>No Obfuscation</option>
            <option value="true">Base64 Scramble</option>
        `;
        c3 = ensureSelect(c3, obfOpts);

        desc.textContent = "Creates split RAR archives. Select naming and obfuscation options.";

    } else if (type === 'github_publish') {
        // Config 1: Repo (Hybrid with Datalist)
        c1 = ensureInput(c1, 'gh-repo-list');
        c1.placeholder = "Repo (user/repo)";

        // Config 2: Account ID (Hybrid with Datalist + OnChange)
        c2 = ensureInput(c2, 'gh-acc-list');
        c2.placeholder = "Account ID";
        c2.onchange = function() { window.fetchReposForAccount(this); };

        // Config 3: Obfuscate Title (Dropdown)
        const obfTitleOpts = `
            <option value="false" selected>No (Original Title)</option>
            <option value="true">Yes (Base64 Scramble)</option>
        `;
        c3 = ensureSelect(c3, obfTitleOpts);

        desc.textContent = "Uploads archives. Obfuscation uses Base64 Release Titles.";

    } else if (type === 'enrich_metadata') {
        c1 = ensureInput(c1); c2 = ensureInput(c2); c3 = ensureInput(c3);
        c1.placeholder = "Reference URL (e.g. IMDB/Wikipedia)";
        c2.style.display = 'none';
        c3.style.display = 'none';
        if(cLong) cLong.style.display = 'block';
        desc.textContent = "Injects custom URL and Long Description into the catalog entry.";

    } else if (type === 'catalog_add') {
        // Config 1: Category (Hybrid Datalist)
        c1 = ensureInput(c1, 'cat-datalist');
        c1.placeholder = "Category (Movies/4K)";

        // Config 2: Priority (Dropdown)
        const priOpts = `
            <option value="2">🔥 Necessary (High)</option>
            <option value="1" selected>Normal</option>
            <option value="0">💤 Unnecessary (Low)</option>
        `;
        c2 = ensureSelect(c2, priOpts);

        // Config 3: Tags (TOKENIZER)
        // Check if already tokenizer?
        if (!c3.classList.contains('tag-container')) {
            // Convert to tokenizer
            c3 = createTagInput(c3, 'tag-datalist');
        }
        c3.style.display = 'flex'; // Ensure flex for container

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
        let conf3Value = ''; // Handle special value for tags

        // Get conf3 element
        const c3El = div.querySelector('.wf-conf-3');
        if (c3El.classList.contains('tag-container')) {
            // It's a tokenizer, get value from hidden input
            conf3Value = c3El.querySelector('.tag-value').value;
        } else {
            conf3Value = c3El.value;
        }

        const conf3 = conf3Value;
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
            // Include tags in config
            config = {
                category: conf1 || 'General',
                priority: parseInt(conf2) || 1,
                tags: conf3 // Capture tags string
            };
        }

        steps.push({ type: type, config: config });
    });

    if(!name || steps.length === 0) {
        alert("Name and at least one step required.");
        return;
    }

    try {
        if (currentEditingId) {
             await fetch(`/api/automation/workflows/${currentEditingId}`, {
                method: 'PUT',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ name: name, steps: steps })
            });
            showToast("Workflow Updated!");
        } else {
            await fetch('/api/automation/workflows', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ name: name, steps: steps })
            });
            showToast("Workflow Saved!");
        }

        document.getElementById('workflow-modal').style.display = 'none';
        currentEditingId = null;
        loadWorkflows();
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
window.editWorkflow = editWorkflow;
window.addWorkflowStepUI = addWorkflowStepUI;
window.saveWorkflow = saveWorkflow;
window.runWorkflow = runWorkflow;
window.deleteWorkflow = deleteWorkflow;
window.updateStepConfigUI = updateStepConfigUI;
