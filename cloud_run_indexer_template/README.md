# Cloud Run Indexer Template

This folder contains a complete, deployable Flask application designed to serve as your "Private Media Catalog".

## 🚀 Deployment Guide

### 1. Setup Your "Bridge" Repository
1.  Create a **Private** GitHub Repository (e.g., `my-media-index`).
2.  This repo will store your `catalog.json` (pushed by ParFix).

### 2. Deploy to Google Cloud Run
You can deploy this directly from source if you have the `gcloud` CLI installed, or push this code to a GitHub repo and connect it to Cloud Run.

#### Option A: Manual Deploy (gcloud CLI)
1.  Navigate to this folder.
2.  Run:
    ```bash
    gcloud run deploy my-index --source . --allow-unauthenticated
    ```
3.  **Note:** `--allow-unauthenticated` makes it public. You probably want to set up authentication later or use Cloud Run's built-in auth.

#### Option B: GitHub Connection (Recommended)
1.  Push the contents of this folder to a new GitHub Repository (e.g., `indexer-app`).
2.  Go to **Google Cloud Console** -> **Cloud Run**.
3.  Click **Create Service**.
4.  Select **"Continuously deploy from a repository"**.
5.  Select your `indexer-app` repo.

### 3. Configuration
Once the service is created, go to **"Edit & Deploy New Revision"** -> **"Variables & Secrets"**.

Add the following Environment Variables:

| Variable | Value | Description |
| :--- | :--- | :--- |
| `CATALOG_URL` | `https://raw.githubusercontent.com/<User>/<Repo>/main/catalog.json` | The raw link to your Bridge Repo's JSON. |
| `GITHUB_TOKEN` | `ghp_...` | A Personal Access Token (Classic) with `repo` scope to read the private JSON. |

### 4. Updates
*   **Content:** ParFix updates `catalog.json` in the Bridge Repo. The website updates instantly on refresh.
*   **Code:** Push changes to this `indexer-app` repo to trigger a new Cloud Run deployment.
