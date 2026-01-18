# ParFix Web Utility

A lightweight, automated repair tool for scrambled Usenet/Debrid downloads.
Designed to solve the specific "Scrambled RARs with Correct PAR2" issue.

## Features

- **Wildcard Repair:** Forces `par2` to scan all files in a directory, fixing cases where filenames don't match.
- **Smart Cleanup:** Renames scrambled files to match the Master PAR2 name.
- **Auto-Extract:** Automatically extracts the archive after successful repair.
- **Lightweight:** Uses Python Flask and raw HTML/JS. No heavy frameworks.
- **Dockerized:** Pre-configured with non-free `unrar` and `par2`.

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
    image: ghcr.io/tvkk0539/rclone-arr-setup-with-jules-customised/parfix:latest
    container_name: parfix
    ports:
      - "5001:5000"  # Access via http://YOUR_IP:5001
    environment:
      - DOWNLOAD_ROOT=/data/downloads
    volumes:
      # CRITICAL: Change the left side to match your real downloads folder!
      - /path/to/your/real/downloads:/data/downloads
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 200M
```

## 🔒 Firewall & Ports

**Which port needs to be open?**
- **Port 5001 (TCP)**

**Scenario 1: Direct Access**
If you want to access the tool directly via `http://YOUR_SERVER_IP:5001`, you **MUST open Port 5001** in your VPS Firewall (GCP Firewall, AWS Security Group, UFW, etc.).
- *GCP Example:* Create a firewall rule allowing `tcp:5001` on Ingress.

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
3. Click **"Repair & Extract Here"**.
4. Watch the logs. The tool will:
   - Run `par2` on all files.
   - Fix the filenames.
   - Extract the video file.

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
