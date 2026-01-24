/* catalog.js - Manages the 'Netflix-style' Catalog View */

const catalog = {
    state: {
        items: [],
        currentFilter: 'all'
    },

    init: async () => {
        await catalog.load();
        catalog.setupEvents();
    },

    load: async () => {
        try {
            const res = await fetch('/api/catalog');
            const data = await res.json();
            catalog.state.items = data;
            catalog.render();
        } catch (e) {
            console.error("Failed to load catalog:", e);
        }
    },

    setupEvents: () => {
        // Add Filter listeners if we add filter UI later
    },

    filter: (query) => {
        const term = query.toLowerCase();
        catalog.render(item => {
            if(!term) return true;
            return item.title.toLowerCase().includes(term) ||
                   (item.category && item.category.toLowerCase().includes(term));
        });
    },

    render: (filterFn = null) => {
        const container = document.getElementById('catalog-grid');
        if (!container) return;

        container.innerHTML = '';

        // Apply filter if provided, otherwise show all
        const itemsToShow = filterFn ? catalog.state.items.filter(filterFn) : catalog.state.items;

        if (itemsToShow.length === 0) {
            const msg = catalog.state.items.length === 0
                ? 'No items in library. Import items from Files view.'
                : 'No matches found.';
            container.innerHTML = `<div class="catalog-empty">${msg}</div>`;
            return;
        }

        itemsToShow.forEach(item => {
            const card = document.createElement('div');
            card.className = 'catalog-card';

            // Placeholder for image (using First Letter)
            const initial = item.title ? item.title.charAt(0).toUpperCase() : '?';

            card.innerHTML = `
                <div class="catalog-card-image">
                    <span>${initial}</span>
                </div>
                <div class="catalog-card-content">
                    <div class="catalog-card-title">${item.title}</div>
                    <div class="catalog-card-meta">${item.size_human} • ${item.category}</div>
                </div>
            `;

            card.onclick = () => catalog.openDetail(item);
            container.appendChild(card);
        });
    },

    openDetail: (item) => {
        const modal = document.getElementById('catalog-detail-modal');
        const content = document.getElementById('catalog-detail-content');

        // Initial for poster
        const initial = item.title ? item.title.charAt(0).toUpperCase() : '?';

        // Check for assets
        let extraActions = '';
        let fileInfo = `Filename: <code>${item.file_name}</code>`;

        if (item.assets && item.assets.length > 0) {
            fileInfo = `Contains <strong>${item.assets.length}</strong> files. Total Size: <strong>${item.size_human}</strong>`;
            // Add Copy Links button
            extraActions = `
                <button onclick="catalog.copyLinks('${item.id}')" class="btn btn-info btn-lg" title="Copy all links for JDownloader">
                    📋 Copy Links (JD)
                </button>
            `;
        }

        content.innerHTML = `
            <div class="catalog-hero">
                <div class="catalog-poster">
                    <span>${initial}</span>
                </div>
                <div class="catalog-info">
                    <h1>${item.title}</h1>
                    <div class="catalog-tags">
                        <span class="tag">${item.category}</span>
                        <span class="tag">${item.size_human}</span>
                        <span class="tag">${item.created_at.substring(0, 10)}</span>
                        ${item.is_encrypted ? '<span class="tag tag-secure">Encrypted</span>' : ''}
                    </div>

                    <p class="catalog-desc">
                        Securely archived in your private library.
                        <br>${fileInfo}
                    </p>

                    <div class="catalog-actions">
                        <a href="${item.release_url}" target="_blank" class="btn btn-primary btn-lg">
                            <i class="fas fa-download"></i> Open Release
                        </a>
                        ${extraActions}
                        <button onclick="catalog.deleteItem('${item.id}')" class="btn btn-danger">
                            <i class="fas fa-trash"></i> Remove
                        </button>
                    </div>
                </div>
            </div>
        `;

        modal.classList.add('active');
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

    submitAdd: () => {
        const title = document.getElementById('cat-add-title').value;
        const url = document.getElementById('cat-add-url').value;
        const cat = document.getElementById('cat-add-category').value || 'General';
        const filename = document.getElementById('cat-add-filename').value || 'Unknown';
        const size = parseInt(document.getElementById('cat-add-size').value) || 0;

        // Parse hidden assets
        let assets = [];
        try {
            const raw = document.getElementById('cat-add-assets').value;
            if(raw) assets = JSON.parse(raw);
        } catch(e) {}

        if (!title || !url) {
            alert("Title and URL are required.");
            return;
        }

        catalog.manualAdd({
            title: title,
            url: url,
            category: cat,
            file_name: filename,
            size_bytes: size,
            assets: assets
        });

        document.getElementById('catalog-add-modal').style.display = 'none';
    },

    deleteItem: async (id) => {
        if (!confirm("Remove this item from your catalog? (Does not delete file from cloud)")) return;

        try {
            await fetch(`/api/catalog/${id}`, { method: 'DELETE' });
            catalog.closeDetail();
            catalog.load(); // Refresh
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
                catalog.load(); // Refresh background
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
