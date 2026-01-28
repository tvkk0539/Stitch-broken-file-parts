/* stealth.js - Manages Stealth Templates for Camouflage Import */

const stealth = {
    init: async () => {
        await stealth.loadTemplates();
    },

    loadTemplates: async () => {
        try {
            const res = await fetch('/api/settings/config');
            const config = await res.json();
            const templates = config.stealth_templates || [];

            const textarea = document.getElementById('stealth-templates-input');
            if (textarea) {
                textarea.value = templates.join('\n');
                stealth.updateCount(templates.length);
            }
        } catch (e) {
            console.error("Failed to load stealth templates:", e);
        }
    },

    saveTemplates: async () => {
        const textarea = document.getElementById('stealth-templates-input');
        if (!textarea) return;

        const raw = textarea.value;
        // Filter empty lines
        const templates = raw.split('\n').map(l => l.trim()).filter(l => l.length > 0);

        try {
            // First load existing to preserve other settings
            const res = await fetch('/api/settings/config');
            const config = await res.json();

            config.stealth_templates = templates;

            const saveRes = await fetch('/api/settings/config', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(config)
            });

            if (saveRes.ok) {
                showToast(`Saved ${templates.length} templates!`, 'success');
                stealth.updateCount(templates.length);
            } else {
                alert("Failed to save templates.");
            }
        } catch (e) {
            alert("Save Error: " + e);
        }
    },

    updateCount: (count) => {
        const el = document.getElementById('stealth-count');
        if (el) el.textContent = `${count} templates loaded`;
    }
};

// Auto-init when view switches to stealth or on load
document.addEventListener('DOMContentLoaded', () => {
    // We can lazy load when tab is clicked or just init
    // automation.js usually handles main init, but we can hook here
});
