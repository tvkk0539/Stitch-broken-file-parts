# Dynamic Storage Pooling (Smart Allocation)

This document details the **Dynamic Storage Pooling** feature, which maximizes storage efficiency across multiple GitHub accounts by reusing existing repositories instead of constantly creating new ones.

## 1. The Concept

Traditional splitting systems use a "Fire and Forget" strategy:
1.  Create `Repo-01`.
2.  Fill it.
3.  Move to `Repo-02`.

If `Repo-01` has a 40GB limit but you only uploaded a 5GB file, that remaining **35GB** is effectively lost/wasted because the system never checks back.

**Dynamic Pooling** changes this. It treats repositories as "Storage Buckets" that can be refilled until they are truly full.

## 2. Modes of Operation

The "GitHub Publish" workflow step now has two **Allocation Modes**:

### A. Create New (Fire & Forget) 🆕
*   **Behavior:** Always creates a new repository sequence (e.g., `Backup-05`, `Backup-06`) or uses the next empty slot.
*   **Best For:** **Stealth & Security**.
*   **Why:** A repository that is created, filled once, and never touched again generates the least amount of "activity heat" on GitHub. It looks like a static archive.

### B. Fill Existing (Pool Efficiency) ♻️
*   **Behavior:**
    1.  Scans the account for *any* repository matching the Base Name (e.g., `Movies-*`).
    2.  Checks the *current* size of each via the API.
    3.  If a repository has space (Size < Limit), it **reuses** it.
    4.  It appends the new file to a new Release tag within that existing repo.
*   **Best For:** **Efficiency & Cost**.
*   **Why:** It ensures you use 100% of the available 40GB/repo and 45GB/account limits.

## 3. Technical Implementation

### The Scanner (`find_available_pool_repo`)
When 'Fill' mode is active, the system runs a pre-flight scan:

```python
# Pseudo-code
candidates = list_repos(pattern="BaseName*")
for repo in candidates:
    size = get_repo_size(repo)
    if size < limit:
        return repo # Found a bucket with space!
return None # No space, create new
```

### Safety & Integrity
*   **Conflict Prevention:** The system creates unique Release Tags (e.g., `v{Date}_{Name}`) so uploading a new file to an old repo never overwrites existing data.
*   **Tracking:** The **Smart Spanning Map** (introduced in the previous update) still tracks exactly where the file went. Even if `Movie A` is in `Repo-01` and `Movie B` is later added to `Repo-01`, the Catalog knows exactly which Release/Asset corresponds to which item.

## 4. Workflow Configuration

To use this feature:
1.  Go to **Automation**.
2.  Add/Edit a **GitHub Publish** step.
3.  Look for **Allocation Mode**:
    *   Select **Fill Existing (Pool)** to enable recycling.
    *   Select **Create New** to force fresh repositories.

## 5. Summary

| Feature | Fire & Forget (New) | Dynamic Pooling (Fill) |
| :--- | :--- | :--- |
| **Storage Efficiency** | Low (Wastes free space) | **High (100% Usage)** |
| **Stealth Profile** | **Maximum (Static)** | Medium (Active Updates) |
| **Repo Count** | High (Many Repos) | **Low (Fewer Repos)** |
| **Complexity** | Low | Medium |

Choose the mode that best fits your risk profile and storage needs.
