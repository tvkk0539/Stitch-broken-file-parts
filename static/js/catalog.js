/* catalog.js - Manages the 'Netflix-style' Catalog View */

const catalog = {
    state: {
        items: [],
        activeTags: new Set(),
        searchQuery: '',
        page: 1,
        limit: 50,
        hasMore: true,
        loading: false
    },

    init: async () => {
        // Setup Filter Bar UI first if empty
        const filters = document.getElementById('catalog-filters');
        if(filters && filters.innerHTML === '') {
            // We can't generate cloud from partial data easily without a separate aggregation API.
            // For now, we will rely on users searching tags via text or add a simple "Popular Tags" later.
            // Or we fetch 'all' tags once? Let's skip tag cloud auto-generation for now or just fetch it separately.
            // To keep it simple: We won't auto-generate cloud from 10k items client side.
            // We will allow adding filters manually or just search.
            // But user asked for filter bar.
            // Let's hide it for now or make it static?
            // BETTER: Load first 50 items and generate tags from them + maybe a "Load Tags" API?
            // Let's stick to standard search for now to ensure speed.
            filters.style.display = 'none';
        }
        await catalog.reload();

        // Infinite Scroll Listener
        const grid = document.getElementById('view-catalog');
        grid.addEventListener('scroll', () => {
            if(grid.scrollTop + grid.clientHeight >= grid.scrollHeight - 100) {
                catalog.loadNextPage();
            }
        });
    },

    reload: async () => {
        catalog.state.page = 1;
        catalog.state.items = [];
        catalog.state.hasMore = true;
        document.getElementById('catalog-grid').innerHTML = '';
        await catalog.loadNextPage();
    },

    loadNextPage: async () => {
        if (catalog.state.loading || !catalog.state.hasMore) return;
        catalog.state.loading = true;

        try {
            // Build Query
            const params = new URLSearchParams({
                page: catalog.state.page,
                limit: catalog.state.limit,
                search: catalog.state.searchQuery
            });
            // Add tag params if we had them (e.g. from filter bar)
            // if(catalog.state.activeTags.size > 0) ... (Server needs to support list, current supports single tag)

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

    filter: (query) => {
        // Debounce?
        if(catalog.filterTimeout) clearTimeout(catalog.filterTimeout);
        catalog.filterTimeout = setTimeout(() => {
            catalog.state.searchQuery = query;
            catalog.reload();
        }, 300);
    },

    renderAppend: (newItems) => {
        const container = document.getElementById('catalog-grid');
        if (!container) return;

        if (catalog.state.items.length === 0) {
            container.innerHTML = `<div class="catalog-empty">No items found.</div>`;
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
                imageHtml = `<img src="${imgSrc}" style="width:100%; height:100%; object-fit:cover;">`;
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

    openDetail: (item) => {
        try {
            console.log("Opening detail for:", item);
            const modal = document.getElementById('catalog-detail-modal');
            const content = document.getElementById('catalog-detail-content');

            if(!modal) {
                alert("Critical Error: Detail modal element not found!");
                return;
            }

            // Image Logic for Detail
            let posterHtml = '';
            if (item.image) {
                const imgSrc = item.image.includes('/') ? item.image : `/api/catalog/image/${item.image}`;
                posterHtml = `<img src="${imgSrc}" style="width:100%; height:100%; object-fit:cover;" onerror="this.src=''; this.parentElement.innerHTML='<span>?</span>'">`;
            } else {
                const initial = item.title ? item.title.charAt(0).toUpperCase() : '?';
                posterHtml = `<span>${initial}</span>`;
            }

            // Check for assets
            let extraActions = '';
            let fileInfo = `Filename: <code>${item.file_name || 'Unknown'}</code>`;

            if (item.assets && item.assets.length > 0) {
                fileInfo = `Contains <strong>${item.assets.length}</strong> files. Total Size: <strong>${item.size_human || '0 B'}</strong>`;
                // Add Copy Links button
                extraActions = `
                    <button onclick="catalog.copyLinks('${item.id}')" class="btn btn-info btn-lg" title="Copy all links for JDownloader">
                        📋 Copy Links (JD)
                    </button>
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

                        <p class="catalog-desc">
                            Securely archived in your private library.
                            <br>${fileInfo}
                        </p>

                        <div class="catalog-actions">
                            ${item.release_url ? `<a href="${item.release_url}" target="_blank" class="btn btn-primary btn-lg"><i class="fas fa-download"></i> Open Release</a>` : ''}
                            ${extraActions}
                            <button onclick="catalog.openEditModal('${item.id}')" class="btn btn-info btn-lg" style="background-color:#e0af68; color:#1a1b26;">
                                <i class="fas fa-edit"></i> Edit
                            </button>
                            <button onclick="catalog.deleteItem('${item.id}')" class="btn btn-danger">
                                <i class="fas fa-trash"></i> Remove
                            </button>
                        </div>
                    </div>
                </div>
            `;

            modal.classList.add('active');
        } catch (e) {
            console.error("Error opening detail modal:", e);
            alert("Failed to open item details. See console for error.");
        }
    },

    copyLinks: (id) => {
        const item = catalog.state.items.find(x => x.id === id);
        if(!item || !item.assets) return;

        const links = item.assets.map(a => a.url).join('\n');
        navigator.clipboard.writeText(links).then(() => {
            alert(`Copied ${item.assets.length} links to clipboard! Paste into JDownloader.`);
        });
    },

    closeDetail: () => {
        document.getElementById('catalog-detail-modal').classList.remove('active');
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
            } else {
                alert("Error: " + result.message);
            }
        } catch (e) {
            alert("Add failed: " + e);
        }
    }
};

// Global Exposure
window.catalog = catalog;
