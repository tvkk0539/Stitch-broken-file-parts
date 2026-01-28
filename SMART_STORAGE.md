# 🧠 Smart Storage: Identity-Aware Camouflage Protocol

ParFix introduces a professional-grade enhancement to the Cold Storage Protocol called **Smart Identity**. This ensures seamless restoration of data scattered across multiple private GitHub accounts.

## ⚠️ The Problem with Standard Scatter/Relay

In a typical "Scatter" backup scenario, you might split a 100GB archive across 3 different GitHub accounts to maximize speed and stay within limits:
*   **File 1** -> `Account A (Private Repo)`
*   **File 2** -> `Account B (Private Repo)`
*   **File 3** -> `Account C (Private Repo)`

**The Challenge:**
When you try to download these files later (Restore), a standard downloader asks for *one* API Token.
*   If you use **Account A's Token**, it can download File 1, but gets `404 Not Found` for File 2 and 3 (because they are in private repos owned by others).
*   Previously, you had to manually download files one by one, switching logins.

## ✅ The Solution: Smart Identity Protocol

ParFix now embeds the **Source Identity** (Account ID & Username) directly into the Media Catalog index for *every single file*.

### 1. Smart Publishing
When `GitHubManager.smart_publish_job` runs (via Automation):
1.  It uploads the file.
2.  It records exactly **which account** was used for that specific file.
3.  It tags the asset in the Catalog DB with `{ "account_id": "123", "username": "UserA" }`.

### 2. Identity-Aware Restoration
When you trigger a **Smart Download**:
1.  The Downloader scans the list of files.
2.  It detects the `account_id` tag on each file.
3.  **Dynamic Token Switching:**
    *   For File 1, it swaps to **Token A**.
    *   For File 2, it swaps to **Token B**.
    *   For File 3, it swaps to **Token C**.
4.  Result: A seamless, single-click restore process that "just works," regardless of how scattered your data is.

### 3. Self-Healing Links (Resilience)
What happens if you rename your GitHub account (e.g., `UserA` -> `UserNew`)?
*   Normally, the stored download links (`github.com/UserA/...`) would eventually break.
*   **ParFix Self-Healing:** The downloader checks your current configuration. If it detects that Account ID `123` is now `UserNew`, but the link says `UserA`, it **automatically repairs the URL** on the fly before downloading.
*   **Result:** Your backup is resilient even against GitHub username changes.

## 🛠️ How to Use

### Setup
1.  Go to **Apps -> GitHub Manager -> Accounts**.
2.  Add all your GitHub accounts (Tokens).

### Automation
1.  Create a Workflow with **GitHub Publish**.
2.  **Smart Repo Spanning:** This is enabled automatically when you set a **Repo Limit (GB)** (default 40GB).
3.  Choose Strategy: **Scatter** (Round Robin) or **Relay**.
4.  Select *multiple* accounts in the account picker.
5.  Run the workflow.

### Verification
1.  Go to the **Catalog**.
2.  Click on your new item.
3.  Expand the **Direct Download Links**.
4.  You will see a tag `👤 Username` next to each file, confirming its source identity.

### Restoration
1.  **Smart Download:** Click the **"🚀 Smart Download"** button in the Catalog Item details.
2.  ParFix will ask for a destination folder (default: `Downloads/Title`).
3.  The system downloads all files to your server, switching tokens automatically.
4.  **Restore:** Once downloaded, click **"♻️ Restore Files"** (if Camouflage was used) to decrypt and rename them back to the original filenames.
