# ParFix & Archive Utility

A lightweight web utility for **Repairing** and **Creating** archives.

## Features

### 🔧 Repair & Extract
Designed to solve the "Scrambled RARs" issue often found with Debrid/Usenet downloads.
- **Wildcard Repair:** Forces `par2` to scan all files, fixing scrambled filenames.
- **Auto-Extract:** Automatically extracts the movie/game after repair.

### 📦 Create Archives (Packer)
Easily create multi-part archives from large files or folders.
- **Split Archives:** Create `.part001.rar` files (e.g., 500MB, 1GB, 2GB chunks).
- **Store Mode:** Uses zero compression (`-m0`) for maximum speed.
- **Password Protection:** Optional encryption for your archives.

### ⚡ General
- **Lightweight:** Uses Python Flask and raw HTML/JS. No heavy frameworks.
- **Dockerized:** Pre-configured with `unrar` and `rar`.

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
   - **Split Size:** e.g., 1GB.
   - **Password:** Optional.
4. Click **"Start Packing"**.

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
