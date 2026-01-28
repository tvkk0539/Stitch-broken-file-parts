# Smart Append & Release Context

This document details the **Smart Append** functionality introduced to the Automation Workflow (GitHub Publish Step). This feature bridges the gap between automated "Fire & Forget" backups and manual, curated archive management.

## 1. Release Mode Strategy

The Automation UI now exposes a **"Release Mode"** dropdown with two distinct behaviors:

### A. ✨ Create New Tag (Default)
*   **Behavior:** The system generates a unique release tag (e.g., `v20240128_backup`) based on the current date and item title.
*   **Use Case:** Daily backups, distinct snapshots, or when you want total separation between uploads.
*   **Conflict:** If a tag already exists, it will fail or try to find a new unique name (depending on configuration).

### B. 📎 Append to Latest (Smart)
*   **Behavior:** The system scans the target repository for the **latest existing release**.
*   **Action:** Instead of creating a new tag, it uploads the new files into that *existing* release bucket.
*   **Fallback:** If no release exists yet, it gracefully falls back to "Create New" mode automatically (Self-Healing).
*   **Use Case:** Filling up a specific "Storage Node" repository (e.g., "Movies-Node-01") until it hits the 2GB limit per release, regardless of dates.

## 2. Smart Context Adoption

When **Append Mode** is active, the system engages the **Adaptive Camouflage** engine to ensure consistency.

**The Problem:**
If you have an existing release disguised as **"AI Model Weights"** containing `model_layer_01.bin`, and you upload a new file disguised as **"System Logs"** (`sys_log_...`), it looks suspicious and messy.

**The Solution (Context Adoption):**
1.  **Scan:** Before uploading, the system reads the metadata of the *existing* release.
2.  **Detect:** It identifies the camouflage template used (e.g., "Detected: AI Weights").
3.  **Adopt:** It forces the *new* upload to use the **same template**, ignoring your default settings if they differ.
    *   *Result:* The new file is renamed to `model_layer_...` to match its neighbors.

## 3. Intelligent Sequence Incrementing

To make the "Append" look like a natural continuation of the project, the system analyzes the filenames already present.

**Logic:**
*   **Existing:** `model_layer_01.bin`, `model_layer_02.bin`
*   **Upload:** The system parses the sequence `02`.
*   **Action:** It names the new file `model_layer_03.bin`.

**Supported Patterns:**
*   **AI Weights:** `model_layer_XX.bin`
*   **DB Backup:** `pg_wal_....000000XX`
*   **Crash Dump:** `core.dump....XX.dmp`

This ensures that even if you upload files weeks apart, they assemble into a coherent, numbered sequence within the repository.
