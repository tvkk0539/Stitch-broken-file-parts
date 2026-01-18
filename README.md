# ParFix Web Utility

A lightweight, automated repair tool for scrambled Usenet/Debrid downloads.
Designed to solve the specific "Scrambled RARs with Correct PAR2" issue.

## Features

- **Wildcard Repair:** Forces `par2` to scan all files in a directory, fixing cases where filenames don't match.
- **Smart Cleanup:** Renames scrambled files to match the Master PAR2 name.
- **Auto-Extract:** Automatically extracts the archive after successful repair.
- **Lightweight:** Uses Python Flask and raw HTML/JS. No heavy frameworks.
- **Dockerized:** Pre-configured with non-free `unrar` and `par2`.

## 🚀 How to Add to Your Existing Stack

If you are using the `Rclone-Arr-Setup` (or any Docker-based media stack), follow these steps to add ParFix.

### 1. Copy the Files
Clone this repository or copy the files (`Dockerfile`, `app.py`, `requirements.txt`, `templates/`) into a folder named `parfix` next to your existing `docker-compose.yml`.

### 2. Update Your `docker-compose.yml`
Add the following service block to your existing `docker-compose.yml`.

**CRITICAL:** Ensure the `volumes` match what your qBittorrent/Radarr containers use!

```yaml
  parfix:
    build: ./parfix  # Path to where you put these files
    container_name: parfix
    ports:
      - "5001:5000"  # Access via http://localhost:5001
    environment:
      - DOWNLOAD_ROOT=/data/downloads
    volumes:
      # MAP THIS TO YOUR EXISTING DOWNLOADS FOLDER!
      # Example: If qBittorrent saves to /mnt/data/torrents, use that here.
      - /path/to/your/real/downloads:/data/downloads
    restart: unless-stopped
```

### 3. Build and Run
```bash
docker-compose up -d --build
```

## 🛠 Usage

1. Open `http://localhost:5001` in your browser.
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
