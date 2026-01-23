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

    render: () => {
        const container = document.getElementById('catalog-grid');
        if (!container) return;

        container.innerHTML = '';

        if (catalog.state.items.length === 0) {
            container.innerHTML = '<div class="catalog-empty">No items in library. Import items from Files view.</div>';
            return;
        }

        catalog.state.items.forEach(item => {
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
                        Filename: <code>${item.file_name}</code>
                    </p>

                    <div class="catalog-actions">
                        <a href="${item.release_url}" target="_blank" class="btn btn-primary btn-lg">
                            <i class="fas fa-download"></i> Download Archive
                        </a>
                        <button onclick="catalog.deleteItem('${item.id}')" class="btn btn-danger">
                            <i class="fas fa-trash"></i> Remove from Catalog
                        </button>
                    </div>
                </div>
            </div>
        `;

        modal.classList.add('active');
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
    },

    submitAdd: () => {
        const title = document.getElementById('cat-add-title').value;
        const url = document.getElementById('cat-add-url').value;
        const cat = document.getElementById('cat-add-category').value || 'General';
        const filename = document.getElementById('cat-add-filename').value || 'Unknown';
        const size = parseInt(document.getElementById('cat-add-size').value) || 0;

        if (!title || !url) {
            alert("Title and URL are required.");
            return;
        }

        catalog.manualAdd({
            title: title,
            url: url,
            category: cat,
            file_name: filename,
            size_bytes: size
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
