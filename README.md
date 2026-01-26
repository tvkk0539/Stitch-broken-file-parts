# ParFix & Archive Utility

A lightweight web utility for **Repairing** and **Creating** archives, managing
files, and syncing to the cloud. Now features a professional **Media Catalog**, **Data Bridge**, and **Automation Engine**.

## Features

### 🔧 Repair & Extract
Designed to solve the "Scrambled RARs" issue often found with Debrid/Usenet down
loads.
- **Wildcard Repair:** Forces `par2` to scan all files, fixing scrambled filenam
es.
- **Auto-Extract:** Automatically extracts the movie/game after repair.
- **Universal Extract (Upgraded):** Unpack RAR, 7-Zip, Zip, ISO, Tar, and more with a single click.

### 📦 Create Archives (Packer)
Easily create multi-part archives from large files or folders.
- **Format:** Choose between **RAR** (Industry Standard) or **7-Zip**.
- **PAR2 Protection:** Automatically generates `.par2` recovery files (10%) to p
rotect against future data corruption (Bit rot).
- **Split Archives:** Create `.part001.rar` files (e.g., 500MB, 1GB, 2GB chunks)
.
- **Store Mode:** Uses zero compression (`-m0`) for maximum speed.
- **Password Protection:** Optional encryption for your archives.
- **Naming Schemes:** Supports `part1.rar`, `part01.rar`, and `part001.rar` standards.
- **Recovery Record:** Optional 5% RAR Recovery Record (`-rr5p`) added inside the archive.

### 🗜️ Compressor (New!)
A versatile tool for general compression and disc image creation.
- **Formats:** 7z, Zip, Tar, Tar.Gz, Tar.Bz2, and **ISO**.
- **Levels:** Adjustable compression from "Store" (Fastest) to "Ultra".
- **Encryption:** Secure 7z/Zip files with AES-256.

### 🎥 Media Catalog (Professional)
A built-in "Personal Netflix" to organize your archived media.
- **SQLite Engine:** Powered by SQLite (`catalog.db`) for massive scalability (10,000+ items) and instant search.
- **Infinite Scroll:** Browse huge libraries smoothly without pagination clicks.
- **Advanced Filtering:** Filter by **Smart Tags** (Tag Cloud) and Search simultaneously.
- **Smart Fetch:** Paste a GitHub Release URL to auto-fill Title, Size, and fetch all asset links.
- **JDownloader Ready:** "Copy Links (JD)" button copies all asset URLs to clipboard for easy downloading.
- **Poster Images:** Upload poster images or paste URLs. Images are securely stored and synced.
- **Data Sync Bridge:** Securely backup your private catalog and images to a **Private GitHub Repository** while keeping the application code public.

### 🤖 Automation Engine (New!)
A powerful workflow system for "One-Click DevOps".
- **Visual Pipelines:** Create custom workflows like "Pack -> Upload -> Catalog".
- **Intelligent Analysis:** Scans source folders for cover images (`cover.jpg`) and builds a detailed file tree for indexing.
- **Stealth Mode:** Obfuscate filenames and release titles with **Base64 Encoding** for privacy.
- **Smart Cataloging:** Automatically adds processed items to your library, tagging them as "No-Cover" if artwork is missing.
- **Pre-Flight Checks:** Blocks execution if Data Sync is not configured, ensuring data safety.

### ☁️ Cloud File Manager (Professional)
Transform your VPS into a Cloud Manager. No FUSE required.
- **Remote Browser:** Browse your Rclone Remotes (Google Drive, OneDrive, etc.)
just like local folders.
- **Cloud-to-Cloud Transfer:** Move or Copy files between different cloud provid
ers directly (e.g., GDrive -> OneDrive) without consuming local storage.
- **Cloud Operations:** Rename, Delete, and Create Folders directly in the cloud
.
- **Download to VPS:** Select files in the cloud and download them to a specific
 folder on your server.
- **Config Upload:** Upload your `rclone.conf` directly from the Settings menu.

### 🧩 Apps & Utilities
A section for integrated tools and utilities.
- **GitHub Release Manager:**
    - **Multi-Account Support:** Login with multiple GitHub accounts and switch
between them instantly using the **Account Hub**.
    - **Repository Browser:** View all your repositories (Public/Private)
 in a convenient grid with **Live Search** to quickly find specific repos.
    - **Direct Code Browser:** Browse repository files and folders direct
ly in the UI without cloning.
        - **View & Edit:** Open text files in a built-in editor and commit chang
es directly to GitHub.
        - **Upload:** Upload files from your **PC** or **Server (VPS)** directly
 to any folder in the repository.
        - **Manage:** Create new folders, delete files, and switch branches (`ma
in`, `dev`, etc.).
    - **Visibility Control:** Toggle repositories between **Public** and **Priva
te** directly from the dashboard.
    - **Create & Import:** Create new empty repositories or **Import** existing
ones from other URLs (supports mirroring public/private repos).
    - **Clone Source:** Clone the source code of any repository to your VPS usin
g `git clone` (authenticated).
    - **Actions Manager:** Full CI/CD Dashboard. View workflows, trigger runs, a
nd cancel active jobs.
    - **Rich Publishing:**
        - Create professional releases with Markdown release notes, **Draft** mo
de, and **Pre-release** tags.
        - **Release Selector:** Fetch and select an existing release to upload a
ssets to.
    - **Downloader & Release Manager:**
        - **Multi-Version Support:** Browse the full history of releases with **
Pagination** (Next/Prev) support.
        - **Live Filter:** Instantly search through releases by tag or filename.
        - **Batch Download:** "Download All" button to grab every asset in a rel
ease simultaneously with parallel processing.

### 📂 Local File Management
- **Full File Browser:** Navigate your mapped directories easily.
- **Move & Copy:** Organize files with a built-in **Folder Browser** to select d
estinations easily.
- **Rename:** Quickly rename files or folders directly from the UI.
- **Create Folder:** Create new directories for better organization (now availab
le inside the Move/Copy selector too).
- **Delete:** Manually delete files/folders to clean up space.
- **Multi-Select:** Check multiple files/folders to perform batch actions (Uploa
d, Move, Delete, etc.).
- **Media Viewer:** Click on any Image (`.jpg`, `.png`), Video (`.mp4`), or Audio (`.mp3`) file to preview it instantly in a high-quality viewer without downloading.
- **Audio Covers:** Use the **"🎵 Covers"** button to recursively scan folders and extract embedded cover art from audio files to `filename.jpg`.

### 🛡️ Stability & UX
- **System Dashboard:** Live monitoring of **Disk Space**, **RAM**, and **CPU**
usage prevents server overload.
- **Deep Inspector:** Inspect video files (Resolution, Codec) and Archives (Cont
ent List) instantly without extracting using `mediainfo`.
- **Smart Job Queue:** All heavy tasks (Repair, Pack, Upload, Download) are queu
ed and processed sequentially in the background. This prevents server crashes (O
ut of Memory).
- **Job Management UI:**
    - **Visual Queue:** See exactly what is running and what is waiting in the "
Job Queue" tab.
    - **Cancellation:** Stop any running job or remove pending jobs with a singl
e click.
    - **Detailed Progress:** Click on any running job to see granular details.
- **Toast Notifications:** Modern, non-blocking status popups (Success/Error/Inf
o) replace annoying browser alerts.
- **Health Monitoring:** Includes a Docker `HEALTHCHECK` to ensure the service i
s always running correctly.

## 🚀 Deployment Guide (Detailed)

You have two options to deploy this. Choose **Option B** if you want the easiest
 setup.

### Option A: Build it Yourself (Clone & Build)
Use this if you want to modify the code.

1. **Clone this repo** onto your server.
2. **Build and Run:**
   ```bash
   docker-compose up -d --build
   ```

### Option B: Use the Pre-Built Image (Recommended)
Use this to simply add the tool to your existing stack without downloading the s
ource code manually.

1. Open your `Rclone-Arr-Setup`'s `docker-compose.yml`.
2. Add the service block below.
3. Run `docker-compose up -d`.

```yaml
  parfix:
    # This pulls the ready-made image from GitHub
    image: ghcr.io/tvkk0539/parfix:latest
    container_name: parfix
    ports:
      - "5001:5000"  # Access via http://YOUR_IP:5001
    environment:
      - DOWNLOAD_ROOT=/data/downloads
      - CONFIG_FILE=/config/config.json
    volumes:
      # CRITICAL: Change the left side to match your real downloads folder!
      - /path/to/your/real/downloads:/data/downloads
      # OPTIONAL: Mount a local folder to persist Notification Settings
      - ./parfix-config:/config
      # OPTIONAL: Mount your rclone.conf for Cloud Upload features
      # - /home/user/.config/rclone/rclone.conf:/root/.config/rclone/rclone.conf
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 1G  # 200M is too low for PAR2. Use 1G or remove this block.
```

## 💻 Accessing the Tool

### Local Computer (Laptop/PC)
If you are running this on your own computer (Windows/Mac/Linux with Docker Desk
top):
- **URL:** [http://localhost:5001](http://localhost:5001)

### Remote Server (VPS)
If you are running this on a cloud server (GCP, AWS, DigitalOcean):
- **URL:** `http://YOUR_SERVER_IP:5001`
- **Firewall:** You **MUST open Port 5001** in your VPS Firewall (GCP Firewall,
AWS Security Group, UFW, etc.).
  - *GCP Example:* Create a firewall rule allowing `tcp:5001` on Ingress.

## 🔒 Security & Reverse Proxy

**Scenario 2: Using a Reverse Proxy (Nginx Proxy Manager)**
If you are using Nginx Proxy Manager (included in many Arr stacks):
1. **Do NOT** open port 5001 to the public internet.
2. In Nginx Proxy Manager, create a new Proxy Host:
   - **Forward Hostname:** `parfix` (or the container IP)
   - **Forward Port:** `5000` (Note: The internal container port is 5000)
3. This is more secure as only Nginx handles the traffic.

## 🛠 Usage

1. Open the tool in your browser.
2. Navigate to the folder containing the scrambled files.
   - *Note: You will see the scrambled RAR names (e.g., `6rLT...rar`) and the co
rrect PAR2 name.*
3. Click **"Repair & Extract"**.
4. Watch the logs. The tool will:
   - Run `par2` on all files.
   - Fix the filenames.
   - Extract the video file.

### Apps Section (New!)
Click the **Apps** icon in the sidebar to access additional utilities.

#### GitHub Release Manager
1. **Manage Accounts:**
   - Click the GitHub Manager card to enter the **Account Hub**.
   - Click **"+ Add Account"** and paste your Personal Access Token (PAT).
   - See your avatar and username instantly verified.
2. **Download:**
   - Select an account from the hub.
   - Enter a GitHub repository (e.g., `radarr/radarr`).
    - **My Repos:** Browse your personal and organizational repositories.
    - **Select:** Click any repo to auto-fill it for Downloading or Publishing.
    - **Toggle Visibility:** Use the lock/unlock icon to switch between Public a
nd Private visibility.
    - **Create Repo:** Click the big "+" card to create a new empty repository.
    - **Import Repo:** Click the "Import" card to mirror an existing repository
(Public or Private) to your account.
    - **Search:** Use the search bar to filter your repository list instantly.
    - **Actions:** Click the "▶" button on any card to open the Actions Dashboar
d (Run/Cancel workflows).
    - **Code Browser:** Click the "📂" folder icon to browse code, edit files, an
d upload content (PC or Server).
3. **Download & Manage Releases:**
    - Enter a GitHub repository (e.g., `radarr/radarr`) or select one from "My R
epos".
    - Click "Fetch" to see releases.
    - **Browse:** Navigate through release history using the Pagination controls
.
    - **Filter:** Type in the search bar to find specific versions or filenames
(e.g., "beta" or ".zip").
    - **Download:** Click the download icon next to an asset, or "Download All"
to grab everything.
    - **Manage:** Use the Trash icons to delete assets or releases (if you own t
he repo).
    - **Clone Source:** Click "Clone Source" to `git clone` the entire repositor
y to your VPS.
4. **Publish:**
   - Select an account (must have write access).
   - Switch to the "Publisher" tab.
   - **Option A (New):** Click "Fetch Releases" to select an existing tag.
   - **Option B (Create):** Manually enter a new Tag (e.g., `v1.0.0`).
   - Select a file to upload.
   - (Optional) Add **Release Notes**, mark as **Draft**, or **Pre-release**.
   - Click "Publish" / "Upload" to finish.

### Using the Media Catalog (New!)
1. Click **Catalog** in the sidebar.
2. **Add Items:** Click **+ Add Item**.
3. **Auto-Fill:** Paste a GitHub Release URL and click **Fetch Details** to auto-fill Title, Size, and get download links.
4. **Tags & Images:** Add tags (comma-separated) and upload a Poster Image.
5. **Search:** Use the Search Bar or click on **Tag Pills** to filter your library instantly.
6. **Download:** Click an item -> "Copy Links (JD)" to paste directly into JDownloader.

### Data Sync Bridge (Backup)
Protect your private data (`catalog.db` and images) without exposing it in the public repo.
1. Create a **Private** GitHub Repository (e.g., `my-data-backup`).
2. Go to ParFix **Settings**.
3. Enter the Repo URL and your GitHub Personal Access Token (PAT).
4. Click **Link & Pull Data**.
5. Now, every time you add an item or upload an image, ParFix automatically pushes the change to your private repo.

### Creating an Archive (Pack)
1. Navigate to the file or folder you want to pack.
2. Click **"Pack"**.
3. Select your options:
   - **Format:** RAR (Recommended for Usenet/Scene) or 7-Zip.
   - **Naming:** Choose `part01` or `part001` styles.
   - **Recovery:** Enable "Add RAR Recovery Record".
   - **Split Size:** e.g., 1GB.
   - **PAR2:** Check "Create PAR2 Recovery Files".
4. Click **"Start Packing"**.

### Creating an Archive (Compress)
1. Select items.
2. Click **"Compress"**.
3. Select Format (e.g., **ISO**, **7z**, **Zip**).
4. Select Compression Level (Store to Ultra).
5. Click **"Start Compression"**.

### Running Automation Workflows
1. Click **Automation** in the sidebar.
2. **Create Workflow:** Define a pipeline (e.g., Analyze -> Pack -> Publish -> Catalog).
3. **Configure:** Set Repo, Tag Format (`v{date}`), and Obfuscation (Base64) options.
4. Go to **Files**, select a folder, and click **Run Automation**.
5. ParFix handles the rest, including smart cover detection and syncing.

### Cloud Upload
1. Select the file(s) or folder(s) you want to upload.
2. Click **"Upload"**.
3. Select your Rclone Remote (requires `rclone.conf` mounted).
   - *Note: The default path `ParFix_Uploads/` handles folders intelligently. Fi
les go into root, folders get their own subdirectories automatically.*
4. (Optional) Adjust concurrency settings for faster parallel uploads.
5. Click **"Start Upload"**.
6. Switch to the **Job Queue** tab to monitor progress or cancel the upload.

## 📦 Bare Metal Installation (Debian/Ubuntu)

If you prefer not to use Docker:

1. Run the setup script as root:
   ```bash
   sudo ./setup.sh
   ```
2. Activate the virtual environment:
   ```bash
   source venv/bin/activate
   ```
3. Run the app:
   ```bash
   python app.py
   ```

## 💡 Advanced: Mapping Multiple Folders

Do you have Movies on one drive and Games on another? You can map **multiple** f
olders into the tool by nesting them inside `/data/downloads`.

**Example `docker-compose.yml`:**

```yaml
    volumes:
      # Map Drive A to a subfolder "Movies"
      - /mnt/drive_a/movies:/data/downloads/movies

      # Map Drive B to a subfolder "Games"
      - /mnt/drive_b/games:/data/downloads/games
```

Now when you open ParFix, you will see two folders: `movies` and `games`.
