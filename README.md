# ParFix & Archive Utility

A lightweight web utility for **Repairing** and **Creating** archives, managing files, and syncing to the cloud.

## Features

### 🔧 Repair & Extract
Designed to solve the "Scrambled RARs" issue often found with Debrid/Usenet downloads.
- **Wildcard Repair:** Forces `par2` to scan all files, fixing scrambled filenames.
- **Auto-Extract:** Automatically extracts the movie/game after repair.

### 📦 Create Archives (Packer)
Easily create multi-part archives from large files or folders.
- **Format:** Choose between **RAR** (Industry Standard) or **7-Zip**.
- **PAR2 Protection:** Automatically generates `.par2` recovery files (10%) to protect against future data corruption (Bit rot).
- **Split Archives:** Create `.part001.rar` files (e.g., 500MB, 1GB, 2GB chunks).
- **Store Mode:** Uses zero compression (`-m0`) for maximum speed.
- **Password Protection:** Optional encryption for your archives.

### ☁️ Cloud & Alerts
- **Rclone Integration:** Manually or Automatically upload your files to the cloud (Google Drive, OneDrive, etc.).
- **Parallel Uploads:** Support for concurrent file transfers (default: 4) for faster uploads.
- **Smart Uploads:** Automatically organizes uploads into `ParFix_Uploads/` to keep your cloud clean.
- **Notifications:** Get alerts on Discord or Telegram when jobs complete or fail.

### 📂 File Management
- **Full File Browser:** Navigate your mapped directories easily.
- **Move & Copy:** Organize files with a built-in **Folder Browser** to select destinations easily.
- **Rename:** Quickly rename files or folders directly from the UI.
- **Create Folder:** Create new directories for better organization.
- **Delete:** Manually delete files/folders to clean up space.
- **Multi-Select:** Check multiple files/folders to perform batch actions (Upload, Move, Delete, etc.).

## 🚀 Deployment Guide (Detailed)

You have two options to deploy this. Choose **Option B** if you want the easiest setup.

### Option A: Build it Yourself (Clone & Build)
Use this if you want to modify the code.

1. **Clone this repo** onto your server.
2. **Build and Run:**
   ```bash
   docker-compose up -d --build
   ```

### Option B: Use the Pre-Built Image (Recommended)
Use this to simply add the tool to your existing stack without downloading the source code manually.

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
    volumes:
      # CRITICAL: Change the left side to match your real downloads folder!
      - /path/to/your/real/downloads:/data/downloads
      # OPTIONAL: Mount your rclone.conf for Cloud Upload features
      # - /home/user/.config/rclone/rclone.conf:/root/.config/rclone/rclone.conf
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 200M
```

## 💻 Accessing the Tool

### Local Computer (Laptop/PC)
If you are running this on your own computer (Windows/Mac/Linux with Docker Desktop):
- **URL:** [http://localhost:5001](http://localhost:5001)

### Remote Server (VPS)
If you are running this on a cloud server (GCP, AWS, DigitalOcean):
- **URL:** `http://YOUR_SERVER_IP:5001`
- **Firewall:** You **MUST open Port 5001** in your VPS Firewall (GCP Firewall, AWS Security Group, UFW, etc.).
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
   - *Note: You will see the scrambled RAR names (e.g., `6rLT...rar`) and the correct PAR2 name.*
3. Click **"Repair & Extract"**.
4. Watch the logs. The tool will:
   - Run `par2` on all files.
   - Fix the filenames.
   - Extract the video file.

### Creating an Archive
1. Navigate to the file or folder you want to pack.
2. Click **"Create Archive"**.
3. Select your options:
   - **Format:** RAR (Recommended for Usenet/Scene) or 7-Zip.
   - **Split Size:** e.g., 1GB.
   - **Password:** Optional.
   - **PAR2:** Check "Create PAR2 Recovery Files" (Recommended for long-term storage).
4. Click **"Start Packing"**.

### Cloud Upload
1. Select the file(s) or folder(s) you want to upload.
2. Click **"Upload"**.
3. Select your Rclone Remote (requires `rclone.conf` mounted).
4. (Optional) Adjust concurrency settings for faster parallel uploads.
5. Click **"Start Upload"**. Logs will show detailed progress.

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

Do you have Movies on one drive and Games on another? You can map **multiple** folders into the tool by nesting them inside `/data/downloads`.

**Example `docker-compose.yml`:**

```yaml
    volumes:
      # Map Drive A to a subfolder "Movies"
      - /mnt/drive_a/movies:/data/downloads/movies

      # Map Drive B to a subfolder "Games"
      - /mnt/drive_b/games:/data/downloads/games
```

Now when you open ParFix, you will see two folders: `movies` and `games`.
