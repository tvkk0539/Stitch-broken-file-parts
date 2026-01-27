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
        const c4 = stepDiv.querySelector('.wf-conf-4'); // New Config 4
        const cLong = stepDiv.querySelector('.wf-conf-long');

        if (step.type === 'pack') {
             c1.value = conf.split || '1024M';
             c2.value = conf.naming || 'part001';
             c3.value = (conf.obfuscate === true || conf.obfuscate === 'true') ? 'true' : 'false';

             // Populate Options (c4 is now a div)
             // We need to wait for UI update or handle it here if updated
             // updateStepConfigUI runs before this, so c4 should be the div
             const optsDiv = stepDiv.querySelector('.wf-opts-container');
             if (optsDiv) {
                 optsDiv.querySelector('.wf-opt-par2').checked = (conf.create_par2 !== false); // Default True
                 optsDiv.querySelector('.wf-opt-rr').checked = (conf.recovery !== false); // Default True
                 optsDiv.querySelector('.wf-opt-encname').checked = (conf.encrypt_filenames === true); // Default False
             }
        } else if (step.type === 'github_publish') {
             c1.value = conf.repo || '';
             c2.value = conf.account_id || '';
             c3.value = (conf.obfuscate_title === true || conf.obfuscate_title === 'true') ? 'true' : 'false';

             // Populate Options
             const optsDiv = stepDiv.querySelector('.wf-opts-container');
             if(optsDiv) {
                 optsDiv.querySelector('.wf-gh-content').value = conf.release_content || 'standard';
                 optsDiv.querySelector('.wf-opt-camo').checked = (conf.camouflage === true);
                 optsDiv.querySelector('.wf-opt-span').checked = (conf.span_repos === true);
                 // New options
                 const safeCb = optsDiv.querySelector('.wf-opt-safe');
                 if(safeCb) safeCb.checked = (conf.safety_sleep === true);
                 const rateCb = optsDiv.querySelector('.wf-opt-rate');
                 if(rateCb) rateCb.checked = (conf.rate_limit === true);
             }

             // Populate Account IDs (Tokenizer)
             // c2 is tag container
             const accIds = (conf.account_id || '').split(',').filter(t => t.trim());
             const accInput = c2.querySelector('.tag-input');
             if(accInput) {
                 c2.querySelectorAll('.tag-pill').forEach(p => p.remove());
                 accIds.forEach(t => addTagPill(c2, accInput, t.trim()));
                 updateHiddenTagValue(c2);
             }

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
    const container = document.getElementById('wf-editor-steps');
    const stepDiv = document.createElement('div');
    stepDiv.className = 'wf-step';
    // Enhanced Styling for Full Page
    stepDiv.style.background = 'var(--panel-bg)';
    stepDiv.style.padding = '20px';
    stepDiv.style.marginBottom = '15px';
    stepDiv.style.borderRadius = '8px';
    stepDiv.style.border = '1px solid var(--border-color)';
    stepDiv.style.boxShadow = '0 2px 10px rgba(0,0,0,0.2)';

    stepDiv.innerHTML = `
        <div style="display:flex; justify-content:space-between; margin-bottom:15px; border-bottom:1px solid var(--border-color); padding-bottom:10px;">
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
            <input type="text" class="wf-conf-4" placeholder="Config 4" style="flex:1; display:none;">
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
    let c4 = container.querySelector('.wf-conf-4');
    const cLong = container.querySelector('.wf-conf-long');
    const desc = container.querySelector('.wf-step-desc');

    c1.style.display = 'block'; c2.style.display = 'block'; c3.style.display = 'block';
    c4.style.display = 'none'; // Default hidden
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
            <option value="50M">50 MB</option>
            <option value="100M">100 MB</option>
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

        // Config 2: Naming - HIDDEN for RAR (since we enforce standard naming)
        // We will repurpose C2 for Format Selection eventually?
        // But Automation currently assumes RAR.
        // If we want to support 7z in Automation, we need a Format selector.
        // For now, Pack step is RAR-centric in code.
        // To follow the pattern: Hide Naming for RAR.
        // Since Automation is RAR-only currently (format='rar' hardcoded in saveWorkflow),
        // we should HIDE this field completely to avoid confusion.

        c2.style.display = 'none'; // Hide Naming Scheme
        c2.value = 'part1'; // Default value

        // Config 3: Obfuscation
        const obfOpts = `
            <option value="false">No Obfuscation</option>
            <option value="true" selected>Base64 Scramble</option>
        `;
        c3 = ensureSelect(c3, obfOpts);

        // Config 4: Options (Multi-Checkboxes)
        c4.style.display = 'block';

        // We need a custom container for checkboxes if c4 is a select/input
        // Strategy: Replace c4 with a div container
        let optsDiv = c4;
        if (c4.tagName !== 'DIV' || !c4.classList.contains('wf-opts-container')) {
            optsDiv = document.createElement('div');
            optsDiv.className = 'wf-conf-4 wf-opts-container';
            optsDiv.style.flex = '1';
            optsDiv.style.display = 'flex';
            optsDiv.style.flexDirection = 'column';
            optsDiv.style.gap = '5px';
            optsDiv.style.background = '#1a1b26';
            optsDiv.style.padding = '5px';
            optsDiv.style.border = '1px solid #414868';
            optsDiv.style.maxHeight = '80px';
            optsDiv.style.overflowY = 'auto';
            c4.replaceWith(optsDiv);
        }

        optsDiv.innerHTML = `
            <label style="display:flex; align-items:center; gap:5px; font-size:0.8em; color:#c0caf5;">
                <input type="checkbox" class="wf-opt-par2" checked> Create PAR2
            </label>
            <label style="display:flex; align-items:center; gap:5px; font-size:0.8em; color:#c0caf5;">
                <input type="checkbox" class="wf-opt-rr" checked> Recovery Record
            </label>
            <label style="display:flex; align-items:center; gap:5px; font-size:0.8em; color:#c0caf5;">
                <input type="checkbox" class="wf-opt-encname"> Encrypt File Names
            </label>
        `;

        desc.textContent = "Creates split RAR archives. Configure recovery and encryption options.";

    } else if (type === 'github_publish') {
        // Config 1: Repo (Hybrid with Datalist)
        c1 = ensureInput(c1, 'gh-repo-list');
        c1.placeholder = "Repo (user/repo)";

        // Config 2: Account IDs (Tokenizer for Relay)
        // Check if already tokenizer?
        if (!c2.classList.contains('tag-container')) {
            // Convert to tokenizer using Account Datalist
            c2 = createTagInput(c2, 'gh-acc-list');
        }
        c2.style.display = 'flex';
        // Add specific placeholder to input inside container
        const c2Input = c2.querySelector('.tag-input');
        if(c2Input) c2Input.placeholder = "Add Account IDs (Relay)...";

        // Config 3: Obfuscate Title (Dropdown)
        const obfTitleOpts = `
            <option value="false">No (Original Title)</option>
            <option value="true" selected>Yes (Base64 Scramble)</option>
        `;
        c3 = ensureSelect(c3, obfTitleOpts);

        // Config 4: Options Container (Repo Span + Camouflage + Content)
        c4.style.display = 'block';

        let optsDiv = c4;
        if (c4.tagName !== 'DIV' || !c4.classList.contains('wf-opts-container')) {
            optsDiv = document.createElement('div');
            optsDiv.className = 'wf-conf-4 wf-opts-container';
            optsDiv.style.flex = '1';
            optsDiv.style.display = 'flex';
            optsDiv.style.flexDirection = 'column';
            optsDiv.style.gap = '5px';
            optsDiv.style.background = '#1a1b26';
            optsDiv.style.padding = '5px';
            optsDiv.style.border = '1px solid #414868';
            optsDiv.style.maxHeight = '100px';
            optsDiv.style.overflowY = 'auto';
            c4.replaceWith(optsDiv);
        }

        optsDiv.innerHTML = `
            <div style="margin-bottom:5px;">
                <select class="wf-gh-content" style="width:100%; background:#13141c; color:#c0caf5; border:1px solid #414868; padding:3px;">
                    <option value="standard">Standard Body</option>
                    <option value="tree_only" selected>Tree Only Body</option>
                    <option value="clean">Clean Body</option>
                </select>
            </div>
            <label style="display:flex; align-items:center; gap:5px; font-size:0.8em; color:#c0caf5;" title="Renames files to look like System Logs">
                <input type="checkbox" class="wf-opt-camo"> 🛡️ Camouflage (Cold Storage)
            </label>
            <label style="display:flex; align-items:center; gap:5px; font-size:0.8em; color:#c0caf5;" title="Auto-create new repos if >40GB">
                <input type="checkbox" class="wf-opt-span"> 📦 Smart Repo Spanning (40GB/Repo)
            </label>
            <div style="border-top:1px solid #414868; margin-top:5px; padding-top:5px;">
                <label style="display:flex; align-items:center; gap:5px; font-size:0.8em; color:#c0caf5;" title="Sleep 1 hour when switching accounts">
                    <input type="checkbox" class="wf-opt-safe"> 🛌 Safety Sleep (1hr Relay)
                </label>
                <label style="display:flex; align-items:center; gap:5px; font-size:0.8em; color:#c0caf5;" title="Sleep 15s between files">
                    <input type="checkbox" class="wf-opt-rate"> 🐌 Rate Limit (15s/File)
                </label>
            </div>
        `;

        desc.textContent = "Uploads archives. Supports Multi-Account Relay, Camouflage, and Safety Pauses.";

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
    const name = document.getElementById('wf-editor-name').value;
    const stepDivs = document.querySelectorAll('.wf-step');
    const steps = [];

    stepDivs.forEach(div => {
        const type = div.querySelector('.wf-step-type').value;
        const conf1 = div.querySelector('.wf-conf-1').value;
        const conf2 = div.querySelector('.wf-conf-2').value;
        const conf4 = div.querySelector('.wf-conf-4').value;
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
            // Get Options from c4 div
            const optsDiv = div.querySelector('.wf-opts-container');
            const par2 = optsDiv ? optsDiv.querySelector('.wf-opt-par2').checked : true;
            const rr = optsDiv ? optsDiv.querySelector('.wf-opt-rr').checked : true;
            const encName = optsDiv ? optsDiv.querySelector('.wf-opt-encname').checked : false;

            config = {
                split: conf1 || '1024M',
                naming: conf2 || 'part001',
                format: 'rar',
                recovery: rr,
                create_par2: par2,
                encrypt_filenames: encName,
                obfuscate: (conf3 && conf3.toLowerCase() === 'true')
            };
        } else if(type === 'github_publish') {
            // Get Options from c4 div
            const optsDiv = div.querySelector('.wf-opts-container');
            const content = optsDiv ? optsDiv.querySelector('.wf-gh-content').value : 'standard';
            const camo = optsDiv ? optsDiv.querySelector('.wf-opt-camo').checked : false;
            const span = optsDiv ? optsDiv.querySelector('.wf-opt-span').checked : false;
            const safe = optsDiv ? optsDiv.querySelector('.wf-opt-safe').checked : false;
            const rate = optsDiv ? optsDiv.querySelector('.wf-opt-rate').checked : false;

            // Get Account IDs from Tokenizer (c2)
            // c2 is div.tag-container
            let accIds = '';
            if (div.querySelector('.wf-conf-2').classList.contains('tag-container')) {
                 accIds = div.querySelector('.wf-conf-2 .tag-value').value;
            } else {
                 accIds = conf2; // Fallback
            }

            config = {
                repo: conf1,
                account_id: accIds, // Comma separated list
                obfuscate_title: (conf3 && conf3.toLowerCase() === 'true'),
                release_content: content,
                camouflage: camo,
                span_repos: span,
                safety_sleep: safe,
                rate_limit: rate,
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
window.updateStepConfigUI = updateStepConfigUI;
