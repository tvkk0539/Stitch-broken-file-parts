# Add log-tab styles
css_content = """

/* Log Tabs */
.log-tab {
    background: #15161e;
    color: var(--text-muted);
    border: 1px solid var(--border-color);
    padding: 8px 15px;
    border-radius: 4px;
    cursor: pointer;
    font-size: 0.9em;
    white-space: nowrap;
    transition: all 0.2s;
}

.log-tab:hover {
    background: #2f3549;
    color: var(--text-color);
}

.log-tab.active {
    background: var(--accent-color);
    color: #1a1b26;
    border-color: var(--accent-color);
    font-weight: bold;
}
"""

with open("static/css/style.css", "a") as f:
    f.write(css_content)
