# Account Routing Table and Strict Mode Update

I have successfully implemented the **Account Routing Table** and **Strict Mode** logic. Here is a detailed explanation of the updates:

### 1. Frontend Updates (`automation.js`)

I completely overhauled the "GitHub Publish" step configuration interface to be more professional and explicit.

*   **New Distribution Routing Table**:
    *   Replaced the old "Relay Accounts" (comma-separated list) and simple "Repository" inputs.
    *   Introduced a dynamic **Routing Table**. You can now add rows specifying exactly: `Account ID` → `Target Repository`.
    *   **Why**: This gives you absolute control. Instead of the system guessing where files go (e.g., `archive-01`, `archive-02`), you explicitly tell it: *"Account A fills `backup/movies`, then Account B fills `backup/tv`"*.

*   **Strict Mode Validation**:
    *   Added a safety check in the UI. If you enable **Strict Mode** (which enforces a 1-Repo-per-Account rule), the system now requires you to define **at least 2 routes**.
    *   **Why**: Strict Mode is a safety net. If Account A fills up, the system *must* have a second account to switch to immediately. If you only have one, Strict Mode would just stop the upload, so the UI prevents this invalid configuration.

### 2. Backend Updates (`GitHubManager` & `WorkflowManager`)

I updated the core logic to handle this new "Map" data structure and enforce the strict safety rules.

*   **Logic - "Map" vs "Legacy"**:
    *   The system now detects if a `distribution_map` is provided.
    *   **Map Mode**: It iterates through your defined rows. Row 1 is Account A + Repo A. Row 2 is Account B + Repo B.
    *   **Legacy Mode**: If you use old workflows, it falls back to the old behavior (Account List + Base Repo Name + Auto-Suffixing `-01`, `-02`).

*   **Strict Mode Logic**:
    *   **Standard Behavior (Relay)**: Normally, if a repo fills up, the system tries to create `repo-02` on the *same* account. It only switches accounts if the *Account Limit* is reached.
    *   **Strict Mode Behavior**: Now, if Strict Mode is ON, the "Repo Limit" (45GB) becomes a hard trigger.
    *   **The Switch**: As soon as the current repo + new file exceeds 45GB, the system **immediately forces an account switch** to the next row in your table. It does *not* try to create a second repo on the same account. This ensures maximum safety for "Cold Storage" accounts.

*   **Fix in `ensure_repo`**:
    *   I found and fixed a bug where providing a full repo name (e.g., `user/repo`) from the new table caused the system to try and create `user/user/repo`. The system now smartly detects if the owner name is already present and normalizes it.

### 3. Verification

*   **Unit Tests**: I created a new test suite (`tests/managers/test_github_routing.py`) that simulates a 45GB upload scenario. It confirmed that when Strict Mode is active, the system correctly abandons the full account and switches to the next one defined in the map.
*   **UI Verification**: I verified the code changes in `automation.js` to ensure the table rows are generated and saved correctly.

This update effectively turns the "GitHub Publish" step into a professional **Distribution Engine**, allowing precise routing of assets across your fleet of accounts.
