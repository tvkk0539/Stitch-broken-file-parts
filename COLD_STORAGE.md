# ❄️ Cold Storage & Camouflage Protocol Guide

This document provides a deep dive into the **ParFix Cold Storage Protocol**, designed for the secure, stealthy, and distributed archival of large datasets (100GB+) to private GitHub repositories.

---

## 🛡️ Deep Dive: Camouflage Mode + Relay (Sequential)

This workflow is designed for **stealth** and **scale**. It assumes you have a large dataset (e.g., 100GB) and multiple GitHub accounts (e.g., UserA, UserB) and want to fill them up one by one.

### 1. The Setup (What happens in the background)
*   **Camouflage**: Renames file chunks (e.g., `Movie.part1.rar`) to look like boring system files (e.g., `sys_log_2023...dat`) to hide contents from deep packet inspection or casual browsing.
*   **Relay Strategy**: This means "fill up one account/repo entirely, then move to the next". It prioritizes organization and minimizing the number of active accounts at any given time.
*   **Smart Spanning**: Automatically creates new repositories (e.g., `repo-01`, `repo-02`) if one gets too big (default 40GB limit).

### 2. The Step-by-Step Execution Loop

**Scenario:** You are uploading **100 files** (1GB each) using "Relay" with **2 Accounts** (UserA, UserB).

1.  **Initialization**:
    *   System checks **Account 1** (UserA).
    *   System checks **Repo 1** (`backup-repo-01`). If missing, it **Creates it (Private)**.
    *   System creates a Release on Repo 1 with the "Boring Template" (e.g., *"Log Rotation v2024"*).

2.  **Uploading (File 1 to File 40)**:
    *   The system uploads `sys_log_...01.dat` through `sys_log_...40.dat` to `backup-repo-01` on **UserA**.
    *   It continues sequentially until it hits the **Repo Span Limit** (e.g., 40GB).

3.  **The Relay Switch (Repo Full)**:
    *   Once `backup-repo-01` hits 40GB, the system decides to switch.
    *   It automatically creates **`backup-repo-02`** on **UserA**.
    *   It creates the "Log Rotation" Release on the new repo.
    *   It continues uploading **File 41-45**.

4.  **The Account Switch (Account Full)**:
    *   Once UserA has uploaded **45GB** total (spanning 2 repos), the **Account Limit** is hit.
    *   **Safety Sleep**: The system pauses (e.g., **1 hour**) to let the API "cool down" and prevent velocity flags.
    *   **Switch**: The system switches context to **UserB**.
    *   It creates **`backup-repo-03`** on **UserB** (preserving the numbering sequence).
    *   It resumes uploading **File 46-100** to UserB.

### 3. The Result (Where your data lives)
*   **UserA / backup-repo-01**: Holds Files 1-40.
*   **UserA / backup-repo-02**: Holds Files 41-45.
*   **UserB / backup-repo-03**: Holds Files 46-100.

---

## 🔀 Deep Dive: Camouflage Mode + Scatter (Round Robin)

This workflow is designed for **speed** and **maximum distribution**. Instead of filling one account, it sprays files across *all* available accounts simultaneously (in turns). This makes the traffic pattern look much more organic and less like a bulk backup.

### 1. The Setup
*   **Scatter Strategy**: "Round Robin" distribution. File 1 goes to Account A, File 2 goes to Account B, File 3 goes to Account C, etc.
*   **Parallelism**: Allows you to leverage the API limits of *multiple* accounts at the same time, effectively multiplying your daily upload quota.

### 2. The Step-by-Step Execution Loop

**Scenario:** You are uploading **100 files** (1GB each) using "Scatter" with **4 Accounts** (UserA, UserB, UserC, UserD).

1.  **Initialization**:
    *   System prepares connections to **all 4 accounts**.
    *   System ensures `backup-repo-01` exists on **ALL 4 accounts** (UserA/backup-repo-01, UserB/backup-repo-01, etc.).

2.  **The Scatter Loop**:
    *   **File 1** (`sys_log_...01.dat`): Uploads to **UserA** / `backup-repo-01`.
    *   **File 2** (`sys_log_...02.dat`): Uploads to **UserB** / `backup-repo-01`.
    *   **File 3** (`sys_log_...03.dat`): Uploads to **UserC** / `backup-repo-01`.
    *   **File 4** (`sys_log_...04.dat`): Uploads to **UserD** / `backup-repo-01`.
    *   **File 5** (`sys_log_...05.dat`): Cycles back to **UserA** / `backup-repo-01`.

3.  **Handling Limits**:
    *   Because the load is split 4 ways, each account only receives ~25GB.
    *   No single account hits the 45GB limit, so **no long Safety Sleep** is triggered during the job.
    *   This is much faster for medium-sized backups (e.g., 100GB split across 4 users = 25GB each, keeping everyone safe).

### 3. The Result (Distributed Storage)
*   **UserA**: Holds Files 1, 5, 9, 13...
*   **UserB**: Holds Files 2, 6, 10, 14...
*   **UserC**: Holds Files 3, 7, 11, 15...
*   **UserD**: Holds Files 4, 8, 12, 16...

---

## ♻️ Deep Dive: Restoration Protocol

So you have 100 "System Logs" spread across the internet. How do you get your `Movie.mkv` back?

### 1. The Key: The Restore Map
When you uploaded the files, ParFix created a secret dictionary called the **Restore Map**.
*   It looks like this:
    ```json
    {
        "sys_log_2023_a1.dat": "MyMovie.part01.rar",
        "sys_log_2023_b2.dat": "MyMovie.part02.rar"
    }
    ```
*   This map is saved in your **Local Database** (`catalog.db`) and physically on your server at `/data/downloads/maps/`.
*   ⚠️ **Crucial**: This map is **NEVER** uploaded to GitHub. It is the only link between the "garbage" logs and your real data.

### 2. The Restoration Process

1.  **Download**:
    *   First, you download the files from GitHub. You can use the "Batch Download" feature or `wget`.
    *   Place all the `.dat` files into a single folder on your server (e.g., `/data/downloads/Restored_Raw/`).

2.  **Trigger Restore**:
    *   Open the **Catalog** in ParFix.
    *   Find your item (e.g., "My Backup").
    *   Click the **"♻️ Restore Files"** button (only visible if a Map exists).

3.  **Path Selection**:
    *   The system asks: *"Where are the files?"*
    *   You enter: `Restored_Raw/`.

4.  **De-Obfuscation (The Magic)**:
    *   The system loads the **Restore Map** from the database.
    *   It scans `Restored_Raw/`.
    *   It sees `sys_log_2023_a1.dat`. It checks the map.
    *   *"Aha! This is actually MyMovie.part01.rar."*
    *   It **Renames** the file instantly.

5.  **Completion**:
    *   Once finished, your folder now contains `MyMovie.part01.rar`, `part02.rar`, etc.
    *   You can now **Extract** them normally using the ParFix "Extract" action or WinRAR.
