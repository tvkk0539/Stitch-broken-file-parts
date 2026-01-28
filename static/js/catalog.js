/* catalog.js - Manages the 'Netflix-style' Catalog View with Sidebar */

const catalog = {
    state: {
        items: [],
        currentCategory: null,
        currentTags: [], // Changed from single tag to array
        currentPriority: null,
        searchQuery: '',
        page: 1,
        limit: 50,
        hasMore: true,
        loading: false
    },

    init: async () => {
        await catalog.loadCategories();
        await catalog.loadTags();
        await catalog.reload();

        // Infinite Scroll Listener
        const grid = document.getElementById('catalog-grid');
        if(grid) {
            grid.addEventListener('scroll', () => {
                if(grid.scrollTop + grid.clientHeight >= grid.scrollHeight - 100) {
                    catalog.loadNextPage();
                }
            });
        }
    },

    loadCategories: async () => {
        try {
            const res = await fetch('/api/catalog/categories');
            const cats = await res.json();
            const list = document.getElementById('catalog-categories-list');
            if(!list) return;

            list.innerHTML = '';
            cats.forEach(cat => {
                const item = document.createElement('div');
                item.className = 'cat-sidebar-item';
                item.textContent = cat;
                item.onclick = () => catalog.filterCategory(cat);
                if (catalog.state.currentCategory === cat) item.classList.add('active');
                list.appendChild(item);
            });
        } catch(e) { console.error("Load categories failed", e); }
    },

    filterCategory: (cat) => {
        catalog.state.currentCategory = cat;

        // Update UI highlighting
        document.querySelectorAll('.cat-sidebar-item').forEach(el => {
            el.classList.remove('active');
            if (el.textContent === cat || (cat === null && el.textContent.trim() === 'All Categories')) {
                el.classList.add('active');
            }
        });

        // Special check for "All Categories" div which might be separate
        if (cat === null) {
             const allBtn = document.querySelector('.cat-sidebar-item[onclick="catalog.filterCategory(null)"]');
             if(allBtn) allBtn.classList.add('active');
        }

        catalog.reload();
    },

    loadTags: async () => {
        try {
            const res = await fetch('/api/catalog/tags');
            const tags = await res.json();
            const datalist = document.getElementById('catalog-tag-datalist');
            if(!datalist) return;

            datalist.innerHTML = '';

            tags.forEach(tag => {
                const opt = document.createElement('option');
                opt.value = tag;
                datalist.appendChild(opt);
            });
        } catch (e) { console.error("Load tags failed", e); }
    },

    handleTagInput: (input) => {
        const val = input.value;
        if (!val) return;

        catalog.addTagFilter(val);
        input.value = ""; // Clear after add
        input.blur(); // Remove focus
    },

    addTagFilter: (tag) => {
        if (!tag) return;
        if (catalog.state.currentTags.includes(tag)) return; // Already added

        catalog.state.currentTags.push(tag);
        catalog.renderActiveTags();
        catalog.reload();
    },

    removeTagFilter: (tag) => {
        catalog.state.currentTags = catalog.state.currentTags.filter(t => t !== tag);
        catalog.renderActiveTags();
        catalog.reload();
    },

    renderActiveTags: () => {
        const container = document.getElementById('catalog-active-tags');
        if (!container) return;
        container.innerHTML = '';

        catalog.state.currentTags.forEach(tag => {
            const pill = document.createElement('div');
            pill.className = 'filter-pill active'; // Re-using existing CSS
            pill.style.display = 'flex';
            pill.style.alignItems = 'center';
            pill.style.gap = '5px';
            pill.innerHTML = `
                <span>${tag}</span>
                <span onclick="catalog.removeTagFilter('${tag}')" style="cursor:pointer; opacity:0.7; font-size:0.8em;" title="Remove">✖</span>
            `;
            container.appendChild(pill);
        });
    },

    filter: (query) => {
        if(catalog.filterTimeout) clearTimeout(catalog.filterTimeout);
        catalog.filterTimeout = setTimeout(() => {
            catalog.state.searchQuery = query;
            catalog.reload();
        }, 300);
    },

    setPriorityFilter: (val) => {
        if (val === "") catalog.state.currentPriority = null;
        else catalog.state.currentPriority = parseInt(val);
        catalog.reload();
    },

    reload: async () => {
        catalog.state.page = 1;
        catalog.state.items = [];
        catalog.state.hasMore = true;

        const grid = document.getElementById('catalog-grid');
        if(grid) grid.innerHTML = '';

        await catalog.loadNextPage();
    },

    loadNextPage: async () => {
        if (catalog.state.loading || !catalog.state.hasMore) return;
        catalog.state.loading = true;

        try {
            // Build Query
            const params = new URLSearchParams({
                page: catalog.state.page,
                limit: catalog.state.limit
            });

            if (catalog.state.searchQuery) params.append('search', catalog.state.searchQuery);
            if (catalog.state.currentCategory) params.append('category', catalog.state.currentCategory);
            if (catalog.state.currentPriority !== null) params.append('priority', catalog.state.currentPriority);

            // Send comma-separated tags
            if (catalog.state.currentTags && catalog.state.currentTags.length > 0) {
                params.append('tags', catalog.state.currentTags.join(','));
            }

            const res = await fetch(`/api/catalog?${params.toString()}`);
            const data = await res.json();

            if (data.length < catalog.state.limit) {
                catalog.state.hasMore = false;
            }

            catalog.state.items = catalog.state.items.concat(data);
            catalog.renderAppend(data);
            catalog.state.page++;

        } catch (e) {
            console.error("Failed to load catalog page:", e);
        } finally {
            catalog.state.loading = false;
        }
    },

    renderAppend: (newItems) => {
        const container = document.getElementById('catalog-grid');
        if (!container) return;

        // Render Hero if this is the first page and we have items
        if (catalog.state.page === 1 && catalog.state.items.length > 0) {
            catalog.renderHero(catalog.state.items[0]);
        } else if (catalog.state.items.length === 0) {
             document.getElementById('catalog-hero-container').innerHTML = ''; // Clear hero if no results
        }

        if (catalog.state.items.length === 0) {
            container.innerHTML = `<div class="catalog-empty">No items found matching your filters.</div>`;
            return;
        }

        // If it was empty message, clear it
        if(container.querySelector('.catalog-empty')) container.innerHTML = '';

        newItems.forEach(item => {
            const card = document.createElement('div');
            card.className = 'catalog-card';

            // Visual Priority Indicator
            if (item.priority == 2) {
                card.style.border = '1px solid #e0af68'; // Gold border for High
                card.style.boxShadow = '0 0 10px rgba(224, 175, 104, 0.2)';
            } else if (item.priority == 0) {
                card.style.opacity = '0.6'; // Dim for Low
            }

            // Image Logic
            let imageHtml = '';
            if (item.image) {
                const imgSrc = item.image.includes('/') ? item.image : `/api/catalog/image/${item.image}`;
                imageHtml = `<img src="${imgSrc}" style="width:100%; height:100%; object-fit:cover;" onerror="this.src=''; this.parentElement.innerHTML='<span>?</span>'">`;
            } else {
                const initial = item.title ? item.title.charAt(0).toUpperCase() : '?';
                imageHtml = `<span>${initial}</span>`;
            }

            // Format Category
            const catDisplay = item.category ? item.category.replace(/\//g, ' › ') : 'Uncategorized';

            card.innerHTML = `
                <div class="catalog-card-image">
                    ${imageHtml}
                </div>
                <div class="catalog-card-content">
                    <div class="catalog-card-title">${item.title}</div>
                    <div class="catalog-card-meta">${item.size_human} • ${catDisplay}</div>
                </div>
            `;

            card.onclick = () => catalog.openDetail(item);
            container.appendChild(card);
        });
    },

    // --- Hero Section Renderer ---
    renderHero: (item) => {
        const heroContainer = document.getElementById('catalog-hero-container');
        if(!heroContainer) return;

        // Image Logic
        let bgStyle = '';
        if (item.image) {
            const imgSrc = item.image.includes('/') ? item.image : `/api/catalog/image/${item.image}`;
            bgStyle = `background-image: url('${imgSrc}');`;
        } else {
            bgStyle = `background: linear-gradient(135deg, #1f2335, #000);`;
        }

        const catDisplay = item.category ? item.category.split('/').pop() : 'Featured';
        const dateStr = item.created_at ? item.created_at.substring(0, 10) : '';

        heroContainer.innerHTML = `
            <div class="hero-banner" style="${bgStyle}">
                <div class="hero-overlay">
                    <div class="hero-content">
                        <div class="hero-label">LATEST ADDITION</div>
                        <h1 class="hero-title">${item.title}</h1>
                        <div class="hero-meta">
                            <span>${catDisplay}</span> • <span>${item.size_human}</span> • <span>${dateStr}</span>
                        </div>
                        <div class="hero-actions">
                             <button onclick="catalog.openDetail(catalog.state.items[0])" class="hero-btn-primary">
                                 ▶ Details
                             </button>
                             ${item.release_url ? `<a href="${item.release_url}" target="_blank" class="hero-btn-secondary">🌍 Open</a>` : ''}
                        </div>
                    </div>
                </div>
            </div>
        `;
    },

    openDetail: (item) => {
        try {
            console.log("Opening detail for:", item);
            const content = document.getElementById('catalog-detail-content');

            // Image Logic for Detail
            let posterHtml = '';
            if (item.image) {
                const imgSrc = item.image.includes('/') ? item.image : `/api/catalog/image/${item.image}`;
                posterHtml = `<img src="${imgSrc}" style="width:100%; height:100%; object-fit:cover;" onerror="this.src=''; this.parentElement.innerHTML='<span>?</span>'">`;
            } else {
                const initial = item.title ? item.title.charAt(0).toUpperCase() : '?';
                posterHtml = `<span>${initial}</span>`;
            }

            // Check for Restore Map
            let restoreBtn = '';
            if (item.restore_map && Object.keys(item.restore_map).length > 0) {
                 restoreBtn = `
                    <button onclick="catalog.restoreItem('${item.id}')" class="btn-lg info-btn" style="background-color: #7aa2f7; color: #15161e; font-weight: bold; border: 2px solid #3d59a1; padding: 10px 20px; font-size:1em; margin-right: 15px;">
                        ♻️ Restore Files
                    </button>
                 `;
            }

            // Check for assets
            let extraActions = '';
            let linksContainerHtml = '';
            let fileInfo = `Filename: <code>${item.file_name || 'Unknown'}</code>`;

            if (item.assets && item.assets.length > 0) {
                fileInfo = `Contains <strong>${item.assets.length}</strong> files. Total Size: <strong>${item.size_human || '0 B'}</strong>`;

                // Build Hidden Links Container
                let linksList = item.assets.map(a => `
                    <div class="link-row">
                        <div style="display:flex;align-items:center;gap:10px; overflow:hidden; flex:1;">
                            <span style="font-size:1.2em;">📦</span>
                            <span class="link-name" title="${a.name}">${a.name}</span>
                        </div>
                        <div style="display:flex; align-items:center; gap:10px;">
                            ${a.username ? `<span class="tag tag-secure" style="font-size:0.8em; padding:2px 6px;" title="Source Account">👤 ${a.username}</span>` : ''}
                            <span class="link-meta">${catalog._formatBytes(a.size)}</span>
                            <button onclick="catalog.copySingleLink('${a.url}')" class="icon-btn" style="padding:4px 8px; font-size:0.9em; background:#2f3549; border:1px solid #414868;" title="Copy Link">📋</button>
                        </div>
                    </div>
                `).join('');

                linksContainerHtml = `
                    <div id="catalog-links-${item.id}" class="catalog-links-dropdown">
                        <h4 style="margin:0 0 10px 0; color:#7dcfff;">Direct Download Links</h4>
                        <div class="links-scroll-area">
                            ${linksList}
                        </div>
                    </div>
                `;

                // Add Buttons (Stacked Layout as requested if applicable, but horizontal fits actions area better)
                // User asked: "make like this button below add the current button expanded direct download links button"
                // This implies the Show Links button should be below the Copy button?
                // Let's use a small vertical flex container for these two specific actions if space permits, or just keep horizontal.
                // Given the layout is flex-row, keeping them side-by-side is safer, but we use the new text.

                extraActions = `
                    <div style="display:flex; flex-direction:column; gap:5px; margin-right:15px;">
                        <button onclick="catalog.downloadItem('${item.id}')" class="btn-lg info-btn" style="background-color: #9ece6a; color: #15161e; font-weight: bold; border: 2px solid #73daca; padding: 10px 20px; font-size:1em;" title="Download to Server (Smart Identity)">
                            🚀 Smart Download
                        </button>
                        <button onclick="catalog.copyLinks('${item.id}')" class="btn-lg info-btn" style="background-color: #00d9ff; color: #15161e; font-weight: bold; border: 2px solid #00b3d4; padding: 10px 20px; font-size:1em;" title="Copy all links for JDownloader">
                            📋 DL Links for JD
                        </button>
                        <button onclick="catalog.toggleLinks('${item.id}')" class="secondary" style="background-color: #2f3549; border: 1px solid #414868; padding: 8px; font-size:0.9em;">
                            ⬇️ Show Links
                        </button>
                    </div>
                `;
            }

            // Breadcrumb category
            const catBreadcrumb = item.category ? item.category.split('/').map(c => `<span class="tag">${c}</span>`).join(' ') : '<span class="tag">General</span>';

            // Tags
            let tagHtml = '';
            if(item.tags && item.tags.length > 0) {
                tagHtml = item.tags.map(t => `<span class="tag tag-secure" style="border-color:#7aa2f7; color:#7aa2f7;">${t}</span>`).join(' ');
            }

            // Date Safe Check
            const dateStr = item.created_at ? item.created_at.substring(0, 10) : 'Unknown Date';

            // --- Parse Description / Tree ---
            let contentsHtml = '';
            let rawDesc = item.description || '';
            const b64Marker = "**Original Structure (Base64):**";

            // Split rawDesc into two parts: Tree (if any) and Rest
            let treeHtml = '';
            let restDesc = rawDesc;

            if (rawDesc.includes(b64Marker)) {
                try {
                    let parts = rawDesc.split(b64Marker);
                    // part[0] is header/intro, part[1] is tree + rest
                    if (parts.length > 1) {
                        let afterMarker = parts[1];
                        // We expect tree in backticks `...`
                        // Format: ...\n`{B64}`\n...
                        let subParts = afterMarker.split('`');
                        if (subParts.length >= 3) {
                            // subParts[0] = newline before tree
                            // subParts[1] = b64
                            // subParts[2] = newline + rest of description
                            let b64 = subParts[1];
                            let extra = subParts[2];

                            restDesc = parts[0] + extra; // Remove the tree part from text description

                            if (b64) {
                                const decoded = atob(b64.trim());
                                const lines = decoded.split('\n');
                                treeHtml = `<div class="catalog-contents-section"><div class="catalog-tree-view"><h3 style="margin-top:0; color:var(--accent-color);">📁 Archive Contents</h3><div class="tree-container">`;
                                lines.forEach(line => {
                                    const cleanLine = line.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
                                    treeHtml += `<div class="tree-row">${cleanLine}</div>`;
                                });
                                treeHtml += `</div></div></div>`;
                            }
                        }
                    }
                } catch(e) { console.error("Tree parse error", e); }
            }

            // Build Description Section (Rich Text)
            // If tree exists, we show it separately.
            // We use restDesc for the text block.

            if (restDesc && restDesc.trim().length > 0) {
                contentsHtml = `<div class="catalog-contents-section"><h3 style="color:var(--accent-color);">📝 Release Notes & Details</h3><div style="background:#16161e; padding:20px; border-radius:8px; border:1px solid var(--border-color); white-space:pre-wrap;">${restDesc.trim()}</div></div>`;
            }

            // Combine
            contentsHtml = treeHtml + contentsHtml;

            // --- Parse & Display Enriched Metadata (Reference URL) ---
            // We look for **Reference:** in the description and turn it into a clickable link
            if (contentsHtml.includes("**Reference:**")) {
                // This is a simple regex replace to make the link clickable in the rendered HTML
                // Note: The `contentsHtml` already contains `rawDesc` inside a div.
                // We will enhance `contentsHtml` to parse links.

                // Safer approach: Re-process `contentsHtml` string? No, messy.
                // Better: If we have contentsHtml (the standard description block), we inject linkify logic.

                // Let's replace the raw text link with an anchor tag.
                // Regex matches: **Reference:**\n(http...)
                // We use [^\\s<]+ to stop before HTML tags or whitespace
                contentsHtml = contentsHtml.replace(
                    /\*\*Reference:\*\*\s*(https?:\/\/[^\s<]+)/g,
                    '<strong style="color:#7dcfff;">Reference:</strong> <a href="$1" target="_blank" style="color:#bb9af7; text-decoration:underline;">$1</a>'
                );

                // Make "Details" bold header
                contentsHtml = contentsHtml.replace(/\*\*Details:\*\*/g, '<h4 style="color:#e0af68; margin-bottom:5px;">Details</h4>');
            }

            content.innerHTML = `
                <div class="catalog-hero">
                    <div class="catalog-poster">
                        ${posterHtml}
                    </div>
                    <div class="catalog-info">
                        <h1>${item.title || 'Untitled'}</h1>
                        <div class="catalog-tags">
                            ${catBreadcrumb}
                            <span class="tag">${item.size_human || '0 B'}</span>
                            <span class="tag">${dateStr}</span>
                            ${item.is_encrypted ? '<span class="tag tag-secure">Encrypted</span>' : ''}
                            ${tagHtml}
                        </div>

                        <div class="catalog-desc">
                            Securely archived in your private library.
                            <br>${fileInfo}
                        </div>

                        <div class="catalog-actions">
                            ${item.release_url ? `<a href="${item.release_url}" target="_blank" class="secondary btn-lg" style="margin-right: 15px;">🌍 Open Release</a>` : ''}
                            ${restoreBtn}
                            ${extraActions}
                            <div style="flex: 1;"></div> <!-- Spacer -->
                            <button onclick="catalog.openEditModal('${item.id}')" class="warning-btn btn-lg" style="color:#1a1b26; margin-right: 15px;">
                                ✏️ Edit
                            </button>
                            <button onclick="catalog.deleteItem('${item.id}')" class="danger btn-lg">
                                🗑️ Remove
                            </button>
                        </div>
                        ${linksContainerHtml}
                    </div>
                </div>
                ${contentsHtml}
            `;

            // Switch View Manually (Simulate SwitchView but custom logic)
            document.querySelectorAll('.view-section').forEach(el => el.classList.remove('active'));
            document.getElementById('view-catalog-detail').classList.add('active');

        } catch (e) {
            console.error("Error opening detail:", e);
            alert("Failed to open item details. See console for error.");
        }
    },

    copyLinks: (id) => {
        const item = catalog.state.items.find(x => x.id === id);
        if(!item || !item.assets) return;

        const links = item.assets.map(a => a.url).join('\n');

        // Robust Copy Logic (Secure & Non-Secure)
        if (navigator.clipboard && window.isSecureContext) {
            navigator.clipboard.writeText(links).then(() => {
                showToast(`Copied ${item.assets.length} links!`, 'success');
            }).catch(err => {
                console.error("Clipboard API failed, trying fallback", err);
                catalog._fallbackCopy(links);
            });
        } else {
            catalog._fallbackCopy(links);
        }
    },

    copySingleLink: (url) => {
        if (navigator.clipboard && window.isSecureContext) {
            navigator.clipboard.writeText(url).then(() => showToast('Link Copied!'));
        } else {
            catalog._fallbackCopy(url);
        }
    },

    _fallbackCopy: (text) => {
        const textArea = document.createElement("textarea");
        textArea.value = text;

        // Ensure it's not visible but part of DOM
        textArea.style.position = "fixed";
        textArea.style.left = "-9999px";
        textArea.style.top = "0";
        document.body.appendChild(textArea);

        textArea.focus();
        textArea.select();

        try {
            const successful = document.execCommand('copy');
            if(successful) showToast('Copied to clipboard!', 'success');
            else showToast('Copy failed.', 'error');
        } catch (err) {
            console.error('Fallback copy failed', err);
            showToast('Copy failed (Browser restriction)', 'error');
        }

        document.body.removeChild(textArea);
    },

    toggleLinks: (id) => {
        const el = document.getElementById(`catalog-links-${id}`);
        if(el.classList.contains('active')) {
            el.classList.remove('active');
        } else {
            el.classList.add('active');
            // Auto scroll to it
            setTimeout(() => el.scrollIntoView({behavior: 'smooth', block: 'center'}), 100);
        }
    },

    _formatBytes: (bytes) => {
        if(bytes===0) return '0 B';
        const k=1024, sizes=['B','KB','MB','GB','TB'];
        const i=Math.floor(Math.log(bytes)/Math.log(k));
        return parseFloat((bytes/Math.pow(k,i)).toFixed(2))+' '+sizes[i];
    },

    closeDetail: () => {
        document.querySelectorAll('.view-section').forEach(el => el.classList.remove('active'));
        document.getElementById('view-catalog').classList.add('active');
    },

    openAddModal: () => {
        document.getElementById('catalog-add-modal').style.display = 'block';
        document.getElementById('cat-add-title').value = '';
        document.getElementById('cat-add-category').value = '';
        document.getElementById('cat-add-priority').value = '1';
        document.getElementById('cat-add-tags').value = '';
        document.getElementById('cat-add-image-text').value = '';
        document.getElementById('cat-add-image-file').value = ''; // Reset file input
        document.getElementById('cat-add-url').value = '';
        document.getElementById('cat-add-filename').value = '';
        document.getElementById('cat-add-size').value = '0';
        document.getElementById('cat-add-assets').value = ''; // Clear hidden assets
    },

    fetchMetadata: async () => {
        const url = document.getElementById('cat-add-url').value;
        if(!url) { alert("Please enter a GitHub Release URL first."); return; }

        const btn = document.querySelector('#catalog-add-modal button.secondary'); // fetch btn
        const originalText = btn.textContent;
        btn.textContent = "Fetching...";
        btn.disabled = true;

        try {
            const res = await fetch('/api/catalog/fetch-metadata', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ url: url })
            });
            const data = await res.json();

            if (data.status === 'success') {
                document.getElementById('cat-add-title').value = data.title;
                document.getElementById('cat-add-size').value = data.total_size;
                document.getElementById('cat-add-filename').value = `${data.file_count} Files`;
                // Store assets JSON in hidden field
                document.getElementById('cat-add-assets').value = JSON.stringify(data.assets);
                showToast(`Fetched ${data.file_count} files!`);
            } else {
                alert("Fetch Error: " + data.error);
            }
        } catch(e) {
            alert("Fetch Failed: " + e);
        } finally {
            btn.textContent = originalText;
            btn.disabled = false;
        }
    },

    submitAdd: async () => {
        const title = document.getElementById('cat-add-title').value;
        const url = document.getElementById('cat-add-url').value;
        const cat = document.getElementById('cat-add-category').value || 'General';
        const priority = parseInt(document.getElementById('cat-add-priority').value) || 1;
        const tagsRaw = document.getElementById('cat-add-tags').value;
        const filename = document.getElementById('cat-add-filename').value || 'Unknown';
        const size = parseInt(document.getElementById('cat-add-size').value) || 0;

        // Image Handling
        const imgText = document.getElementById('cat-add-image-text').value;
        const imgFile = document.getElementById('cat-add-image-file').files[0];
        let imagePath = imgText; // Default to text/url

        if (!title || !url) {
            alert("Title and URL are required.");
            return;
        }

        // Upload Image if File Selected
        if(imgFile) {
            try {
                const optimize = document.getElementById('cat-add-optimize').checked;
                const fd = new FormData();
                fd.append('file', imgFile);
                fd.append('optimize', optimize); // Send flag

                showToast("Uploading Image...");
                const res = await fetch('/api/catalog/upload-image', {method:'POST', body:fd});
                const d = await res.json();
                if(d.status === 'success') {
                    imagePath = d.filename;
                } else {
                    alert("Image Upload Failed: " + d.error);
                    return;
                }
            } catch(e) {
                alert("Image Upload Error: " + e);
                return;
            }
        }

        // Parse Tags
        const tags = tagsRaw.split(',').map(t => t.trim()).filter(t => t.length > 0);

        // Parse hidden assets
        let assets = [];
        try {
            const raw = document.getElementById('cat-add-assets').value;
            if(raw) assets = JSON.parse(raw);
        } catch(e) {}

        catalog.manualAdd({
            title: title,
            url: url,
            category: cat,
            priority: priority,
            tags: tags,
            file_name: filename,
            size_bytes: size,
            assets: assets,
            image: imagePath
        });

        document.getElementById('catalog-add-modal').style.display = 'none';
    },

    openEditModal: (id) => {
        const item = catalog.state.items.find(x => x.id === id);
        if(!item) return;

        document.getElementById('cat-edit-id').value = id;
        document.getElementById('cat-edit-title').value = item.title;
        document.getElementById('cat-edit-category').value = item.category || '';
        document.getElementById('cat-edit-priority').value = item.priority !== undefined ? item.priority : 1;
        document.getElementById('cat-edit-tags').value = (item.tags || []).join(', ');
        document.getElementById('cat-edit-url').value = item.release_url || '';

        // Reset image inputs
        document.getElementById('cat-edit-image-text').value = '';
        document.getElementById('cat-edit-image-file').value = '';

        // Preview
        const preview = document.getElementById('cat-edit-preview');
        if(item.image) {
            preview.src = item.image.includes('/') ? item.image : `/api/catalog/image/${item.image}`;
            preview.style.display = 'block';
        } else {
            preview.style.display = 'none';
        }

        // Close detail, open edit
        catalog.closeDetail();
        document.getElementById('catalog-edit-modal').style.display = 'block';
    },

    submitEdit: async () => {
        const id = document.getElementById('cat-edit-id').value;
        const title = document.getElementById('cat-edit-title').value;
        const category = document.getElementById('cat-edit-category').value;
        const priority = parseInt(document.getElementById('cat-edit-priority').value) || 1;
        const tagsRaw = document.getElementById('cat-edit-tags').value;
        const url = document.getElementById('cat-edit-url').value;

        const imgText = document.getElementById('cat-edit-image-text').value;
        const imgFile = document.getElementById('cat-edit-image-file').files[0];

        let newImage = null;

        // Handle Image Upload if changed
        if(imgFile) {
            try {
                const optimize = document.getElementById('cat-edit-optimize').checked;
                const fd = new FormData();
                fd.append('file', imgFile);
                fd.append('optimize', optimize);

                showToast("Uploading new image...");
                const res = await fetch('/api/catalog/upload-image', {method:'POST', body:fd});
                const d = await res.json();
                if(d.status === 'success') newImage = d.filename;
                else { alert("Image Upload Failed: " + d.error); return; }
            } catch(e) { alert("Upload Error: " + e); return; }
        } else if (imgText) {
            newImage = imgText;
        }

        const tags = tagsRaw.split(',').map(t => t.trim()).filter(t => t.length > 0);

        const payload = {
            title: title,
            category: category,
            priority: priority,
            tags: tags,
            release_url: url
        };
        if(newImage) payload.image = newImage;

        try {
            const res = await fetch(`/api/catalog/${id}`, {
                method: 'PUT',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(payload)
            });
            const d = await res.json();

            if(d.status === 'success') {
                showToast("Item Updated!");
                document.getElementById('catalog-edit-modal').style.display = 'none';
                catalog.reload();
            } else {
                alert("Update Failed: " + (d.error || d.message));
            }
        } catch(e) {
            alert("Update Request Failed: " + e);
        }
    },

    downloadItem: async (id) => {
        const item = catalog.state.items.find(x => x.id === id);
        if(!item) return;

        // Clean title for default path
        const defPath = item.title.replace(/[^a-zA-Z0-9-_]/g, '_');
        const path = prompt("Download to server path (relative to downloads):", defPath);
        if (path === null) return; // Cancelled

        try {
            const res = await fetch('/api/catalog/download', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ item_id: id, path: path })
            });
            const d = await res.json();
            if (d.status === 'queued') {
                showToast("Smart Download Started! 🚀", "success");
            } else {
                alert("Error: " + d.error);
            }
        } catch (e) {
            alert("Request failed: " + e);
        }
    },

    deleteItem: async (id) => {
        if (!confirm("Remove this item from your catalog? (Does not delete file from cloud)")) return;

        try {
            await fetch(`/api/catalog/${id}`, { method: 'DELETE' });
            catalog.closeDetail();
            catalog.reload(); // Refresh
        } catch (e) {
            alert("Failed to delete: " + e);
        }
    },

    restoreItem: async (id) => {
        const path = prompt("Enter the path where the obfuscated files are located (relative to Download Root):", "Downloads/");
        if (!path) return;

        try {
            const res = await fetch('/api/obfuscation/restore', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ item_id: id, path: path })
            });
            const data = await res.json();

            if (data.status === 'queued') {
                showToast(`Restoration Started! Job ID: ${data.job_id}`, 'success');
            } else {
                alert("Error: " + (data.error || "Unknown error"));
            }
        } catch (e) {
            alert("Request failed: " + e);
        }
    },

    // Called from Files View to add an item
    manualAdd: async (fileData) => {
        // fileData = { title, file_name, size_bytes, url, category }
        try {
            const res = await fetch('/api/catalog', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(fileData)
            });
            const result = await res.json();
            if (result.status === 'success') {
                showToast("Added to Catalog!");
                catalog.reload(); // Refresh background
                // Also reload categories in case a new one was added
                catalog.loadCategories();
            } else {
                alert("Error: " + result.message);
            }
        } catch (e) {
            alert("Add failed: " + e);
        }
    },

    toggleSidebar: () => {
        const sb = document.getElementById('catalog-sidebar');
        if (!sb) return;

        if (sb.style.width === '0px' || sb.style.width === '') {
            sb.style.width = '250px';
        } else {
            sb.style.width = '0px';
        }
    }
};

// Global Exposure
window.catalog = catalog;
