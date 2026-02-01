import os
import json
import base64
from datetime import datetime
from app.core.job_manager import log

class SurvivalKitManager:
    """
    Generates a portable "Survival Kit" for Cold Storage archives.
    Includes human-readable manifests and a standalone HTML recovery tool.
    """

    @staticmethod
    def generate_kit(output_dir, job_name, restore_map, spanning_info):
        """
        Creates the kit folder and artifacts.
        output_dir: The folder where the source files were (or where kit should go).
        job_name: Name of the archive/release.
        restore_map: Dict {fake_name: real_name}
        spanning_info: List of dicts [{repo, account, account_id, url, ...}]
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_name = "".join([c for c in job_name if c.isalnum() or c in (' ', '_', '-')]).strip()
            kit_folder_name = f"SURVIVAL_KIT_{safe_name}_{timestamp}"
            kit_path = os.path.join(output_dir, kit_folder_name)

            os.makedirs(kit_path, exist_ok=True)
            log(f"📦 Generating Survival Kit in: {kit_path}")

            # 1. Manifest.txt (Human Readable)
            SurvivalKitManager._create_manifest(kit_path, job_name, restore_map, spanning_info)

            # 2. Identities.json (Machine Readable)
            SurvivalKitManager._create_identities(kit_path, spanning_info)

            # 3. Recovery Tool.html (Standalone App)
            SurvivalKitManager._create_html_tool(kit_path, job_name, restore_map, spanning_info)

            log(f"✅ Survival Kit Generated Successfully.")
            return kit_path

        except Exception as e:
            log(f"❌ Failed to generate Survival Kit: {e}")
            return None

    @staticmethod
    def _create_manifest(kit_path, job_name, restore_map, spanning_info):
        path = os.path.join(kit_path, "manifest.txt")
        with open(path, 'w', encoding='utf-8') as f:
            f.write(f"================================================================\n")
            f.write(f" PARFIX SURVIVAL MANIFEST\n")
            f.write(f" Job: {job_name}\n")
            f.write(f" Date: {datetime.now().isoformat()}\n")
            f.write(f"================================================================\n\n")

            f.write(f"[ STORAGE INFRASTRUCTURE ]\n")
            f.write(f"This archive is distributed across the following locations:\n\n")

            for info in spanning_info:
                f.write(f"  • Repo:    {info.get('repo_name', 'Unknown')}\n")
                f.write(f"    Account: {info.get('account', 'Unknown')} (ID: {info.get('account_id', 'N/A')})\n")
                f.write(f"    URL:     {info.get('url', 'N/A')}\n")
                f.write(f"    Files:   {info.get('file_count', 0)}\n")
                f.write(f"    Size:    {info.get('size_human', '0B')}\n")
                f.write(f"\n")

            f.write(f"================================================================\n")
            f.write(f"[ RESTORE MAPPING ]\n")
            f.write(f"Use this map to rename 'Camouflaged' files back to original.\n")
            f.write(f"Format: Camouflaged_Name -> Original_Name\n\n")

            for fake, real in restore_map.items():
                f.write(f"{fake} -> {real}\n")

    @staticmethod
    def _create_identities(kit_path, spanning_info):
        path = os.path.join(kit_path, "identities.json")
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(spanning_info, f, indent=2)

    @staticmethod
    def _create_html_tool(kit_path, job_name, restore_map, spanning_info):
        """
        Embeds the data into a single HTML file with JS logic.
        """
        # Serialize Data for Embedding
        data_payload = {
            "jobName": job_name,
            "generatedAt": datetime.now().isoformat(),
            "restoreMap": restore_map,
            "infrastructure": spanning_info
        }
        json_payload = json.dumps(data_payload)
        b64_payload = base64.b64encode(json_payload.encode('utf-8')).decode('utf-8')

        # Use html.escape for job_name in title/header
        import html
        safe_title = html.escape(job_name)

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Survival Kit: {safe_title}</title>
    <style>
        :root {{
            --bg: #0f0f14;
            --panel: #1a1b26;
            --text: #a9b1d6;
            --accent: #7aa2f7;
            --success: #9ece6a;
            --border: #2f334d;
        }}
        body {{
            background-color: var(--bg);
            color: var(--text);
            font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            margin: 0;
            padding: 20px;
            line-height: 1.6;
        }}
        .container {{
            max-width: 900px;
            margin: 0 auto;
        }}
        header {{
            border-bottom: 2px solid var(--border);
            padding-bottom: 20px;
            margin-bottom: 30px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        h1 {{ color: #fff; margin: 0; font-size: 1.8rem; }}
        .badge {{
            background: var(--accent);
            color: #1a1b26;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.8rem;
            font-weight: bold;
            text-transform: uppercase;
        }}
        .card {{
            background: var(--panel);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        }}
        h2 {{ color: var(--accent); margin-top: 0; border-bottom: 1px solid var(--border); padding-bottom: 10px; }}

        table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
        th, td {{ text-align: left; padding: 10px; border-bottom: 1px solid var(--border); }}
        th {{ color: #fff; }}
        tr:last-child td {{ border-bottom: none; }}

        .code-block {{
            background: #111;
            padding: 15px;
            border-radius: 6px;
            font-family: 'Consolas', monospace;
            overflow-x: auto;
            color: var(--success);
            border: 1px solid var(--border);
        }}

        .btn {{
            background: var(--accent);
            color: #1a1b26;
            border: none;
            padding: 10px 20px;
            border-radius: 4px;
            cursor: pointer;
            font-weight: bold;
            text-decoration: none;
            display: inline-block;
        }}
        .btn:hover {{ opacity: 0.9; }}

        .tabs {{ display: flex; gap: 10px; margin-bottom: 15px; }}
        .tab {{
            background: var(--panel);
            border: 1px solid var(--border);
            padding: 8px 16px;
            cursor: pointer;
            color: var(--text);
        }}
        .tab.active {{
            background: var(--accent);
            color: #1a1b26;
            border-color: var(--accent);
            font-weight: bold;
        }}
    </style>
</head>
<body>

<div class="container">
    <header>
        <div>
            <h1>Survival Kit</h1>
            <div style="font-size: 0.9rem; margin-top: 5px;">Ref: {safe_title}</div>
        </div>
        <span class="badge">OFFLINE READY</span>
    </header>

    <!-- INFRASTRUCTURE SECTION -->
    <div class="card">
        <h2>🏗️ Storage Infrastructure</h2>
        <p>Your data is distributed across the following secure locations. Use the Account IDs to ensure you are accessing the correct credentials.</p>
        <div style="overflow-x: auto;">
            <table id="infra-table">
                <thead>
                    <tr>
                        <th>Repository</th>
                        <th>Account Identity</th>
                        <th>Location</th>
                        <th>Size</th>
                    </tr>
                </thead>
                <tbody></tbody>
            </table>
        </div>
    </div>

    <!-- RESTORE TOOLS SECTION -->
    <div class="card">
        <h2>🛠️ Restoration Tools</h2>
        <p>Generate a script to rename your camouflaged files back to their original names.</p>

        <div class="tabs">
            <div class="tab active" onclick="switchTab('bat')">Windows (.bat)</div>
            <div class="tab" onclick="switchTab('sh')">Linux/Mac (.sh)</div>
            <div class="tab" onclick="switchTab('raw')">Raw Map</div>
        </div>

        <div id="view-bat" class="view-content">
            <p>Save this code as <code>restore.bat</code> in the folder with your files, then run it.</p>
            <textarea id="code-bat" class="code-block" style="width:100%; height:200px;"></textarea>
            <button class="btn" onclick="download('restore.bat', 'code-bat')" style="margin-top:10px;">💾 Download .bat</button>
        </div>

        <div id="view-sh" class="view-content" style="display:none;">
            <p>Save this code as <code>restore.sh</code>, run <code>chmod +x restore.sh</code>, then <code>./restore.sh</code>.</p>
            <textarea id="code-sh" class="code-block" style="width:100%; height:200px;"></textarea>
            <button class="btn" onclick="download('restore.sh', 'code-sh')" style="margin-top:10px;">💾 Download .sh</button>
        </div>

        <div id="view-raw" class="view-content" style="display:none;">
            <p>Raw JSON mapping for manual reference.</p>
            <textarea id="code-raw" class="code-block" style="width:100%; height:200px;"></textarea>
        </div>
    </div>

    <footer style="text-align: center; font-size: 0.8rem; color: #555; margin-top: 50px;">
        Generated by ParFix Pro | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    </footer>
</div>

<script>
    // Embedded Data Payload
    const PAYLOAD_B64 = "{b64_payload}";

    // Init
    let DATA = {{}};
    try {{
        const json = atob(PAYLOAD_B64);
        DATA = JSON.parse(json);
    }} catch(e) {{
        console.error("Failed to parse embedded data", e);
        document.body.innerHTML = "<h1>Error: Data Corrupted</h1>";
    }}

    // Render Infrastructure
    const infraBody = document.querySelector('#infra-table tbody');
    DATA.infrastructure.forEach(item => {{
        const row = document.createElement('tr');

        // Safer element creation
        const tdRepo = document.createElement('td');
        const bRepo = document.createElement('strong');
        bRepo.textContent = item.repo_name;
        tdRepo.appendChild(bRepo);

        const tdAcc = document.createElement('td');
        const divAcc = document.createElement('div');
        divAcc.textContent = item.account;
        const divId = document.createElement('div');
        divId.style.fontSize = '0.8em';
        divId.style.opacity = '0.7';
        divId.style.fontFamily = 'monospace';
        divId.textContent = 'ID: ' + item.account_id;
        tdAcc.appendChild(divAcc);
        tdAcc.appendChild(divId);

        const tdUrl = document.createElement('td');
        const aUrl = document.createElement('a');
        aUrl.href = item.url;
        aUrl.target = '_blank';
        aUrl.style.color = 'var(--accent)';
        aUrl.textContent = 'Open Release';
        tdUrl.appendChild(aUrl);

        const tdSize = document.createElement('td');
        tdSize.textContent = item.size_human;

        row.appendChild(tdRepo);
        row.appendChild(tdAcc);
        row.appendChild(tdUrl);
        row.appendChild(tdSize);

        infraBody.appendChild(row);
    }});

    // Generate Scripts
    const map = DATA.restoreMap;

    // Windows BAT
    let bat = "@echo off\\n";
    bat += "echo ParFix Restore Script\\n";
    bat += "echo =====================\\n";
    for(const [fake, real] of Object.entries(map)) {{
        bat += `if exist "${{fake}}" ( ren "${{fake}}" "${{real}}" ) else ( echo Missing: ${{fake}} )\\n`;
    }}
    bat += "echo Done.\\npause";
    document.getElementById('code-bat').value = bat;

    // Linux SH
    let sh = "#!/bin/bash\\n";
    sh += "echo 'ParFix Restore Script'\\n";
    for(const [fake, real] of Object.entries(map)) {{
        sh += `[ -f "${{fake}}" ] && mv "${{fake}}" "${{real}}" || echo "Missing: ${{fake}}"\n`;
    }}
    sh += "echo 'Done.'";
    document.getElementById('code-sh').value = sh;

    // Raw
    document.getElementById('code-raw').value = JSON.stringify(map, null, 4);

    // Logic
    function switchTab(mode) {{
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.view-content').forEach(v => v.style.display = 'none');

        // Find clicked tab logic is simple here since we use onclick
        event.target.classList.add('active');
        document.getElementById('view-' + mode).style.display = 'block';
    }}

    function download(filename, sourceId) {{
        const text = document.getElementById(sourceId).value;
        const blob = new Blob([text], {{type: 'text/plain'}});
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        a.click();
        window.URL.revokeObjectURL(url);
    }}
</script>

</body>
</html>"""

        path = os.path.join(kit_path, "recovery_tool.html")
        with open(path, 'w', encoding='utf-8') as f:
            f.write(html_content)
