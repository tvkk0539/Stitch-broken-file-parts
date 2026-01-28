# Smart Spanning & Distribution Protocol

This document details the **Smart Spanning** architecture, a professional-grade distribution system designed to split large archives across multiple GitHub repositories and accounts while maintaining precise tracking and identity integrity.

## 1. Core Concept

When an archive exceeds the capacity of a single repository (e.g., >40GB) or a single GitHub account (e.g., >45GB), the system employs one of two strategies to distribute the files:

*   **Relay Strategy (Sequential):** Fills one repository until the limit is reached, then "relays" to the next repository (e.g., `backup-01` -> `backup-02`). If an account limit is reached, it switches to the next account credential and continues.
*   **Scatter Strategy (Round-Robin):** Distributes files one-by-one across all available accounts in a cycle. This maximizes bandwidth utilization and provides redundancy against single-account takedowns.

## 2. Backend Tracking Logic

The core tracking logic resides in `GitHubManager.smart_publish_job`. Unlike simple uploaders that only track a single URL, this system builds a granular **Spanning Map**.

### The Spanning Map
As files are uploaded, the system aggregates data in memory using a composite key: `account_id|repo_full_name`. This ensures that even if files are scattered randomly, they are grouped correctly by their infrastructure location for the final report.

**Data Structure (Python):**
```python
spanning_map[key] = {
    'repo_name': 'backup-01',    # Short name for display
    'account': 'UserA',          # Mutable Username (for friendly display)
    'account_id': '12345678',    # Immutable GitHub ID (CRITICAL for integrity)
    'url': 'https://...',        # Link to the Release page
    'file_count': 15,            # Number of parts in this shard
    'size_bytes': 10737418240    # Raw size for precise math
}
```

By storing the `account_id`, the system ensures that even if a user changes their GitHub username, the system can self-heal or correctly identify the storage location later.

## 3. Database Persistence

Once the upload job completes, this memory map is serialized into a JSON list and passed to the `CatalogManager`.

*   **Database:** `catalog.db` (SQLite)
*   **Table:** `items`
*   **Column:** `spanning_info` (JSON Type)

The data is permanently stored in the item's record. This decouples the catalog from the physical file state—the catalog "knows" exactly where every byte lives without needing to query GitHub API.

**Stored JSON Example:**
```json
[
  {
    "repo_name": "backup-repo-01",
    "account": "UserSecure",
    "account_id": "99887766",
    "url": "https://github.com/UserSecure/backup-repo-01/releases/tag/v1",
    "size_human": "10.00 GB"
  },
  {
    "repo_name": "backup-repo-02",
    "account": "UserBackup",
    "account_id": "11223344",
    "url": "https://github.com/UserBackup/backup-repo-02/releases/tag/v1",
    "size_human": "5.00 GB"
  }
]
```

## 4. Frontend Visualization

The Catalog UI (`catalog.js`) has been upgraded to render this professional data structure.

*   **Logic:** When opening an item detail modal, the system checks for the existence of `spanning_info`.
*   **Rendering:** If found, it generates the **"Infrastructure & Distribution"** table.
*   **Identity Column:** Displays the `account` (Username) for readability, but also renders the `account_id` (e.g., `ID: 99887766`) in a subtle sub-line. This proves to the user that the system is tracking the *immutable identity* of the storage, not just a fragile username.
*   **Action:** Instead of a generic "Open" button that might lead to a 404 if the file is elsewhere, each row has its own deep link to the specific repository release.

## 5. Data Flow Summary

1.  **Upload:** `GitHubManager` uploads files, switching accounts/repos as needed.
2.  **Track:** Every successful upload updates the in-memory `spanning_map`.
3.  **Persist:** The map is converted to a list and saved to the SQLite `spanning_info` column.
4.  **Display:** `catalog.js` reads this JSON and renders the multi-row Distribution Table, exposing the full infrastructure topology to the user.
