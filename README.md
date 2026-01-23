# ParFix Web Utility Pro

**ParFix Pro** is a powerful, professional-grade media management and archival tool designed for power users, data hoarders, and DevOps enthusiasts. It combines robust file manipulation utilities with a "Netflix-style" media catalog, all reachable via a clean web interface.

## 🚀 Key Features

### 📦 Archiving & Compression
*   **Packer (Archiver):** Create split RAR archives for long-term storage.
    *   **Naming Schemes:** Supports `part1.rar`, `part01.rar`, and `part001.rar` standards.
    *   **Recovery:** Optional 5% RAR Recovery Record (`-rr5p`) and PAR2 file generation.
    *   **Security:** Password protection and obfuscated filenames.
*   **Compressor:** A versatile tool for general compression.
    *   **Formats:** 7z, Zip, Tar, Tar.Gz, Tar.Bz2, and **ISO**.
    *   **Levels:** Adjustable compression from "Store" (Fastest) to "Ultra".
    *   **Encryption:** Secure 7z/Zip files with AES-256.

### 🎥 Media Catalog (Integrated)
*   **Personal Netflix:** Browse your archived media in a beautiful, dark-mode grid view.
*   **Local-First:** Your data lives in a simple `catalog.json` file. No database required.
*   **Data Sync Bridge:** securely backup your private catalog to a **Private GitHub Repository** while keeping the application code public.
*   **Search & Filter:** Instantly find items in your library.

### ☁️ Cloud & GitHub Integration
*   **Rclone Manager:** Seamlessly move data between your server and cloud storage (GDrive, OneDrive, S3, etc.) with parallel transfers.
*   **GitHub Manager:**
    *   **Downloader:** Fetch releases or assets from any public repository.
    *   **Publisher:** Publish releases with rich notes, drafts, and pre-release toggles.
    *   **Repo Browser:** View and edit code in your repositories without cloning.
    *   **Actions Dashboard:** Trigger and monitor CI/CD workflows.

### 🛠️ Utilities
*   **Universal Extract:** Unpack RAR, 7z, Zip, ISO, Tar, and more with a single click.
*   **File Manager:** A robust browser to Move, Copy, Rename, Delete, and Inspect files.
*   **Inspector:** Deep media analysis (Bitrate, Codecs) using `mediainfo`.

---

## 🛠️ Installation

### Option A: Docker (Recommended)
The easiest way to run ParFix Pro.

```bash
# 1. Clone the repo
git clone https://github.com/your-repo/ParFix.git
cd ParFix

# 2. Build and Run
docker-compose up -d --build
```

Access the UI at: `http://localhost:5000`

### Option B: Python (Manual)
Requires Python 3.11+, `ffmpeg`, `mediainfo`, `rclone`, `rar`, `par2`, `genisoimage`.

```bash
# 1. Install System Dependencies (Ubuntu/Debian)
sudo apt update && sudo apt install -y ffmpeg mediainfo rclone par2 genisoimage git

# 2. Install Python Deps
pip install -r requirements.txt

# 3. Run
python3 run.py
```

---

## 📖 Usage Guide

### 1. The "Pack" Workflow
Used for preparing large files for secure cloud storage (e.g., Usenet/Telegram style).
1.  Select a file/folder in the **Files** tab.
2.  Click **Pack**.
3.  Choose your Split Size (e.g., 1GB) and Naming Scheme (e.g., `part001.rar`).
4.  Enable **Recovery Record** for data safety.
5.  Click Start. The job runs in the background.

### 2. The "Compress" Workflow
Used for general file sharing or ISO creation.
1.  Select items.
2.  Click **Compress**.
3.  Select Format (e.g., **ISO** for disc images, **7z** for max compression).
4.  Set Password (optional).

### 3. Setting Up Data Sync (Backup)
Protect your `catalog.json` without exposing it.
1.  Create a **Private** GitHub Repository (e.g., `my-data-backup`).
2.  Go to ParFix **Settings**.
3.  Enter the Repo URL and your GitHub Personal Access Token (PAT).
4.  Click **Link & Pull Data**.
5.  Now, every time you modify the Catalog, ParFix automatically pushes the change to your private repo.

---

## 🛡️ Security Note
*   **Data Separation:** This project is designed to keep your data (`catalog.json`, `config.json`) separate from the code.
*   **Git Ignore:** Sensitive files are strictly ignored by `.gitignore`.
*   **Private Sync:** The Data Sync feature ensures your backups are encrypted (via HTTPS) and stored only in your private repository.

---

## 📄 License
MIT License. Free for personal and professional use.
