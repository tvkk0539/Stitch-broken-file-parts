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

function openWorkflowEditor() {
    currentEditingId = null; // Reset for new

    // Switch View
    switchView('workflow-editor');

    // Reset Form
    document.getElementById('wf-editor-name').value = '';
    document.getElementById('wf-editor-steps').innerHTML = '';
    document.getElementById('wf-editor-title').textContent = "Create Workflow";

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
    openWorkflowEditor(); // Re-use init logic (title/value override below)

    currentEditingId = id;
    document.getElementById('wf-editor-title').textContent = "Edit Workflow";
    document.getElementById('wf-editor-name').value = wf.name;

    const container = document.getElementById('wf-editor-steps');
    container.innerHTML = '';

    wf.steps.forEach(step => {
        const stepDiv = addWorkflowStepUI();
        stepDiv.querySelector('.wf-step-type').value = step.type;
        renderStepUI(stepDiv, step.type, step.config);
    });
}

function addWorkflowStepUI() {
    const container = document.getElementById('wf-editor-steps');
    const stepDiv = document.createElement('div');
    stepDiv.className = 'wf-step';
    stepDiv.style.background = 'var(--panel-bg)';
    stepDiv.style.padding = '20px';
    stepDiv.style.marginBottom = '15px';
    stepDiv.style.borderRadius = '8px';
    stepDiv.style.border = '1px solid var(--border-color)';
    stepDiv.style.boxShadow = '0 2px 10px rgba(0,0,0,0.2)';

    stepDiv.innerHTML = `
        <div style="display:flex; justify-content:space-between; margin-bottom:15px; border-bottom:1px solid var(--border-color); padding-bottom:10px;">
            <select class="wf-step-type" style="width:auto;" onchange="renderStepUI(this.closest('.wf-step'), this.value)">
                <option value="analyze_source">1. Analyze Source (Pre-Index)</option>
                <option value="pack">2. Pack (Archive)</option>
                <option value="github_publish">3. GitHub Publish</option>
                <option value="enrich_metadata">4. Enrich Metadata (Text/URL)</option>
                <option value="catalog_add">5. Add to Catalog</option>
            </select>
            <button class="danger" onclick="this.parentElement.parentElement.remove()" style="padding:2px 8px; font-size:0.8em; flex:0;">X</button>
        </div>
        <div class="wf-step-content">
            <!-- Dynamic Content -->
        </div>
    `;
    container.appendChild(stepDiv);
    // Init with default
    renderStepUI(stepDiv, 'analyze_source');
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


// --- New Form Rendering System ---

function renderStepUI(stepDiv, type, config = {}) {
    const contentDiv = stepDiv.querySelector('.wf-step-content');
    contentDiv.innerHTML = ''; // Clear old

    if (type === 'analyze_source') {
        contentDiv.innerHTML = `
            <div style="padding:10px; color:gray; font-style:italic;">
                No configuration required. Scans the input folder recursively.
            </div>
        `;

    } else if (type === 'pack') {
        contentDiv.innerHTML = `
            <div style="display:grid; grid-template-columns: 1fr 1fr; gap:15px; margin-bottom:15px;">
                <div>
                    <label style="display:block; color:var(--text-muted); font-size:0.8em; margin-bottom:5px;">Split Size</label>
                    <select class="wf-pack-split" style="width:100%; padding:8px; background:#1a1b26; border:1px solid #414868; color:#fff;">
                        <option value="1024M" selected>1 GB (Standard)</option>
                        <option value="2048M">2 GB</option>
                        <option value="5120M">5 GB</option>
                        <option value="50M">50 MB</option>
                        <option value="0">No Split</option>
                    </select>
                </div>
                <div>
                     <label style="display:block; color:var(--text-muted); font-size:0.8em; margin-bottom:5px;">Format</label>
                     <select class="wf-pack-fmt" style="width:100%; padding:8px; background:#1a1b26; border:1px solid #414868; color:#fff;">
                        <option value="rar" selected>RAR</option>
                     </select>
                </div>
            </div>
            <div style="background:#1a1b26; padding:10px; border-radius:4px;">
                <label style="display:block; color:var(--accent-color); font-size:0.8em; margin-bottom:10px;">Security & Protection</label>
                <div style="display:flex; gap:15px; flex-wrap:wrap;">
                    <label style="display:flex; align-items:center; gap:5px; color:#c0caf5;"><input type="checkbox" class="wf-pack-enc" checked> Encrypt Names</label>
                    <label style="display:flex; align-items:center; gap:5px; color:#c0caf5;"><input type="checkbox" class="wf-pack-rr" checked> Recovery Record</label>
                    <label style="display:flex; align-items:center; gap:5px; color:#c0caf5;"><input type="checkbox" class="wf-pack-par2" checked> Create PAR2</label>
                    <label style="display:flex; align-items:center; gap:5px; color:#c0caf5;"><input type="checkbox" class="wf-pack-obf"> Obfuscate (Simple)</label>
                </div>
            </div>
        `;
        // Populate
        if(config.split) contentDiv.querySelector('.wf-pack-split').value = config.split;
        if(config.encrypt_filenames !== undefined) contentDiv.querySelector('.wf-pack-enc').checked = config.encrypt_filenames;
        if(config.recovery !== undefined) contentDiv.querySelector('.wf-pack-rr').checked = config.recovery;
        if(config.create_par2 !== undefined) contentDiv.querySelector('.wf-pack-par2').checked = config.create_par2;
        if(config.obfuscate !== undefined) contentDiv.querySelector('.wf-pack-obf').checked = config.obfuscate;

    } else if (type === 'github_publish') {
        contentDiv.innerHTML = `
            <div style="margin-bottom:15px;">
                <label style="display:block; color:var(--text-muted); font-size:0.8em; margin-bottom:5px;">Repository (Base Name)</label>
                <input type="text" class="wf-gh-repo" placeholder="user/backup-repo" list="gh-repo-list" style="width:100%; padding:10px; background:#1a1b26; border:1px solid #414868; color:#fff;">
            </div>

            <div style="margin-bottom:15px;">
                <label style="display:block; color:var(--text-muted); font-size:0.8em; margin-bottom:5px;">Relay Accounts (Multi-Select)</label>
                <div class="wf-gh-acc-container"></div>
            </div>

            <div style="display:grid; grid-template-columns: 1fr 1fr; gap:15px; margin-bottom:15px;">
                <div>
                     <label style="display:block; color:var(--text-muted); font-size:0.8em; margin-bottom:5px;">Upload Strategy</label>
                     <select class="wf-gh-strat" style="width:100%; padding:8px; background:#1a1b26; border:1px solid #414868; color:#fff;">
                        <option value="relay" selected>🔄 Relay (Sequential)</option>
                        <option value="scatter">🔀 Scatter (Round Robin)</option>
                     </select>
                </div>
                <div>
                     <label style="display:block; color:var(--text-muted); font-size:0.8em; margin-bottom:5px;">Allocation Mode</label>
                     <select class="wf-gh-alloc" style="width:100%; padding:8px; background:#1a1b26; border:1px solid #414868; color:#fff;">
                        <option value="new" selected>🆕 Create New (Fire & Forget)</option>
                        <option value="fill">♻️ Fill Existing (Pool)</option>
                     </select>
                </div>
            </div>

            <div style="margin-bottom:15px;">
                 <label style="display:block; color:var(--text-muted); font-size:0.8em; margin-bottom:5px;">Release Content</label>
                 <select class="wf-gh-content" style="width:100%; padding:8px; background:#1a1b26; border:1px solid #414868; color:#fff;">
                    <option value="tree_only" selected>Tree Only (Stealth)</option>
                    <option value="standard">Standard</option>
                    <option value="clean">Clean</option>
                 </select>
            </div>

            <div class="wf-opts-container" style="background:#15161e; border:1px solid #414868; border-radius:4px; padding:15px;">
                <h4 style="margin:0 0 10px 0; color:#7dcfff; font-size:0.9em; display:flex; align-items:center; gap:5px;">
                    ❄️ Cold Storage Protocol
                </h4>

                <div style="display:flex; flex-wrap:wrap; gap:15px; margin-bottom:10px; align-items:center;">
                    <label style="display:flex; align-items:center; gap:5px; font-size:0.8em; color:#c0caf5;" title="Renames files to look like System Logs">
                        <input type="checkbox" class="wf-opt-camo" onchange="this.parentElement.nextElementSibling.style.display = this.checked ? 'block' : 'none'"> 🛡️ Camouflage Mode
                    </label>

                    <label style="display:flex; align-items:center; gap:5px; font-size:0.8em; color:#c0caf5;" title="Imports a random safe repository template">
                        <input type="checkbox" class="wf-gh-stealth"> 🎭 Use Stealth Import
                    </label>

                    <div style="display:none;" class="wf-camo-template-container">
                        <select class="wf-opt-camo-template" style="padding:2px 5px; background:#1a1b26; border:1px solid #414868; color:#fff; font-size:0.8em; border-radius:4px;">
                             <option value="log_rotation" selected>Log Rotation (Default)</option>
                             <option value="random">🎲 Random Template</option>
                             <option value="crash_dump">💥 Crash Dump</option>
                             <option value="infrastructure">🏗️ Infrastructure</option>
                             <option value="db_backup">🗄️ DB Backup</option>
                             <option value="ai_weights">🧠 AI Weights</option>
                             <option value="cdn_cache">⚡ CDN Cache</option>
                             <option value="debug_symbols">🐛 Debug Symbols</option>
                        </select>
                    </div>

                    <label style="display:flex; align-items:center; gap:5px; font-size:0.8em; color:#c0caf5;" title="Scrambles the Release Title (Base64)">
                        <input type="checkbox" class="wf-gh-obf-title" checked> 🔒 Obfuscate Title
                    </label>
                </div>

                <div style="display:grid; grid-template-columns: 1fr 1fr; gap:10px;">
                    <div>
                        <label style="font-size:0.75em; color:var(--text-muted);">Repo Limit (GB)</label>
                        <input type="number" class="wf-gh-lim-repo" value="40" style="width:100%; background:#1a1b26; border:1px solid #414868; color:#fff; padding:5px;">
                    </div>
                    <div>
                        <label style="font-size:0.75em; color:var(--text-muted);">Account Limit (GB)</label>
                        <input type="number" class="wf-gh-lim-acc" value="45" style="width:100%; background:#1a1b26; border:1px solid #414868; color:#fff; padding:5px;">
                    </div>
                    <div>
                        <label style="font-size:0.75em; color:var(--text-muted);">Safety Sleep (s)</label>
                        <input type="number" class="wf-gh-sleep" value="3600" style="width:100%; background:#1a1b26; border:1px solid #414868; color:#fff; padding:5px;">
                    </div>
                    <div>
                        <label style="font-size:0.75em; color:var(--text-muted);">Rate Limit (s)</label>
                        <input type="number" class="wf-gh-rate" value="15" style="width:100%; background:#1a1b26; border:1px solid #414868; color:#fff; padding:5px;">
                    </div>
                </div>
            </div>
        `;

        // Populate
        if(config.repo) contentDiv.querySelector('.wf-gh-repo').value = config.repo;
        if(config.strategy) contentDiv.querySelector('.wf-gh-strat').value = config.strategy;
        if(config.allocation_mode) contentDiv.querySelector('.wf-gh-alloc').value = config.allocation_mode;
        if(config.release_content) contentDiv.querySelector('.wf-gh-content').value = config.release_content;
        if(config.camouflage !== undefined) {
             const cb = contentDiv.querySelector('.wf-opt-camo');
             cb.checked = config.camouflage;
             // Trigger visibility
             contentDiv.querySelector('.wf-camo-template-container').style.display = config.camouflage ? 'block' : 'none';
        }
        if(config.camo_template) contentDiv.querySelector('.wf-opt-camo-template').value = config.camo_template;

        if(config.obfuscate_title !== undefined) contentDiv.querySelector('.wf-gh-obf-title').checked = config.obfuscate_title;
        if(config.use_stealth_import !== undefined) contentDiv.querySelector('.wf-gh-stealth').checked = config.use_stealth_import;

        if(config.span_limit) contentDiv.querySelector('.wf-gh-lim-repo').value = config.span_limit;
        if(config.account_limit) contentDiv.querySelector('.wf-gh-lim-acc').value = config.account_limit;
        if(config.safety_sleep_seconds) contentDiv.querySelector('.wf-gh-sleep').value = config.safety_sleep_seconds;
        if(config.rate_limit_seconds) contentDiv.querySelector('.wf-gh-rate').value = config.rate_limit_seconds;

        // Tokenizer for Accounts
        const accContainer = contentDiv.querySelector('.wf-gh-acc-container');
        const tokenizer = createTagInput(accContainer, 'gh-acc-list');
        tokenizer.classList.add('wf-gh-acc-tokenizer'); // Add marker for save
        const tokenInput = tokenizer.querySelector('.tag-input');
        tokenInput.placeholder = "Add Account IDs...";

        if(config.account_id) {
            const ids = config.account_id.split(',').filter(x=>x.trim());
            ids.forEach(id => addTagPill(tokenizer, tokenInput, id));
            updateHiddenTagValue(tokenizer);
        }

    } else if (type === 'catalog_add') {
         contentDiv.innerHTML = `
            <div style="margin-bottom:10px;">
                <label style="display:block; color:var(--text-muted); font-size:0.8em; margin-bottom:5px;">Category</label>
                <input type="text" class="wf-cat-cat" placeholder="Movies/4K" list="cat-datalist" style="width:100%; padding:10px; background:#1a1b26; border:1px solid #414868; color:#fff;">
            </div>
            <div style="margin-bottom:10px;">
                <label style="display:block; color:var(--text-muted); font-size:0.8em; margin-bottom:5px;">Priority</label>
                <select class="wf-cat-pri" style="width:100%; padding:8px; background:#1a1b26; border:1px solid #414868; color:#fff;">
                    <option value="2">🔥 Necessary (High)</option>
                    <option value="1" selected>Normal</option>
                    <option value="0">💤 Unnecessary (Low)</option>
                </select>
            </div>
            <div style="margin-bottom:10px;">
                <label style="display:block; color:var(--text-muted); font-size:0.8em; margin-bottom:5px;">Tags</label>
                <div class="wf-cat-tags"></div>
            </div>
         `;
         if(config.category) contentDiv.querySelector('.wf-cat-cat').value = config.category;
         if(config.priority) contentDiv.querySelector('.wf-cat-pri').value = config.priority;

         const tagCont = contentDiv.querySelector('.wf-cat-tags');
         const tagTok = createTagInput(tagCont, 'tag-datalist');
         const tagInp = tagTok.querySelector('.tag-input');
         if(config.tags) {
             config.tags.split(',').forEach(t => addTagPill(tagTok, tagInp, t.trim()));
             updateHiddenTagValue(tagTok);
         }
    } else if (type === 'enrich_metadata') {
         contentDiv.innerHTML = `
            <div style="margin-bottom:10px;">
                <label>Reference URL</label>
                <input type="text" class="wf-meta-url" style="width:100%; padding:10px; background:#1a1b26; border:1px solid #414868; color:#fff;">
            </div>
            <div>
                <label>Description</label>
                <textarea class="wf-meta-desc" style="width:100%; height:100px; padding:10px; background:#1a1b26; border:1px solid #414868; color:#fff;"></textarea>
            </div>
         `;
         if(config.reference_url) contentDiv.querySelector('.wf-meta-url').value = config.reference_url;
         if(config.description) contentDiv.querySelector('.wf-meta-desc').value = config.description;
    }
}

async function saveWorkflow() {
    const name = document.getElementById('wf-editor-name').value;
    const stepDivs = document.querySelectorAll('.wf-step');
    const steps = [];

    stepDivs.forEach(div => {
        const type = div.querySelector('.wf-step-type').value;
        const contentDiv = div.querySelector('.wf-step-content');
        let config = {};

        if (type === 'analyze_source') {
             // No config needed
        } else if (type === 'pack') {
             const split = contentDiv.querySelector('.wf-pack-split').value;
             const fmt = contentDiv.querySelector('.wf-pack-fmt').value;
             const encName = contentDiv.querySelector('.wf-pack-enc').checked;
             const rr = contentDiv.querySelector('.wf-pack-rr').checked;
             const par2 = contentDiv.querySelector('.wf-pack-par2').checked;
             const obf = contentDiv.querySelector('.wf-pack-obf').checked;

             config = {
                 split: split,
                 format: fmt,
                 encrypt_filenames: encName,
                 recovery: rr,
                 create_par2: par2,
                 obfuscate: obf,
                 naming: 'part1' // Default enforced by backend for RAR
             };

        } else if (type === 'github_publish') {
             const repo = contentDiv.querySelector('.wf-gh-repo').value;

             // Account Tokenizer
             const accContainer = contentDiv.querySelector('.wf-gh-acc-tokenizer');
             const accIds = accContainer ? accContainer.querySelector('.tag-value').value : '';

             const strat = contentDiv.querySelector('.wf-gh-strat').value;
             const alloc = contentDiv.querySelector('.wf-gh-alloc').value;
             const content = contentDiv.querySelector('.wf-gh-content').value;

             // Get Options Container
             const optsDiv = div.querySelector('.wf-opts-container');
             const camo = optsDiv ? optsDiv.querySelector('.wf-opt-camo').checked : false;
             const camoTemplate = optsDiv ? optsDiv.querySelector('.wf-opt-camo-template').value : 'log_rotation';
             const obfTitle = optsDiv ? optsDiv.querySelector('.wf-gh-obf-title').checked : true;

             // Stealth Logic
             const stealthCb = optsDiv ? optsDiv.querySelector('.wf-gh-stealth') : null;
             const useStealth = stealthCb ? stealthCb.checked : false;

             const repoLim = parseInt(contentDiv.querySelector('.wf-gh-lim-repo').value) || 40;
             const accLim = parseInt(contentDiv.querySelector('.wf-gh-lim-acc').value) || 45;
             const sleep = parseInt(contentDiv.querySelector('.wf-gh-sleep').value) || 3600;
             const rate = parseInt(contentDiv.querySelector('.wf-gh-rate').value) || 15;

             config = {
                 repo: repo,
                 account_id: accIds,
                 strategy: strat,
                 allocation_mode: alloc,
                 release_content: content,
                 camouflage: camo,
                 camo_template: camoTemplate,
                 obfuscate_title: obfTitle,
                 use_stealth_import: useStealth,
                 span_limit: repoLim,
                 account_limit: accLim,
                 safety_sleep_seconds: sleep,
                 rate_limit_seconds: rate,
                 span_repos: true, // Always active with limits
                 tag_template: 'v{date}_{name}'
             };

        } else if (type === 'catalog_add') {
             const cat = contentDiv.querySelector('.wf-cat-cat').value;
             const pri = contentDiv.querySelector('.wf-cat-pri').value;

             const tagContainer = contentDiv.querySelector('.wf-cat-tags .tag-container');
             const tags = tagContainer ? tagContainer.querySelector('.tag-value').value : '';

             config = {
                 category: cat,
                 priority: parseInt(pri),
                 tags: tags
             };

        } else if (type === 'enrich_metadata') {
             const url = contentDiv.querySelector('.wf-meta-url').value;
             const desc = contentDiv.querySelector('.wf-meta-desc').value;
             config = {
                 reference_url: url,
                 description: desc
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

        closeWorkflowEditor();
        loadWorkflows();
    } catch(e) {
        alert("Save failed: " + e);
    }
}

function closeWorkflowEditor() {
    switchView('automation');
    currentEditingId = null;
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
window.openWorkflowEditor = openWorkflowEditor;
window.closeWorkflowEditor = closeWorkflowEditor;
window.editWorkflow = editWorkflow;
window.addWorkflowStepUI = addWorkflowStepUI;
window.saveWorkflow = saveWorkflow;
window.runWorkflow = runWorkflow;
window.deleteWorkflow = deleteWorkflow;
