import os
import json
import requests
from flask import Flask, render_template, abort

app = Flask(__name__)

# --- Configuration ---
# Set these in your Cloud Run Environment Variables
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
# Format: "https://raw.githubusercontent.com/<user>/<repo>/main/catalog.json"
CATALOG_URL = os.environ.get("CATALOG_URL")

# Fallback for local testing if no URL provided
LOCAL_CATALOG_PATH = "catalog.json"

def get_catalog():
    """
    Fetches the catalog.json from the Private GitHub Repo (The Bridge).
    Falls back to local file if configured.
    """
    if not CATALOG_URL:
        # Local Mode
        if os.path.exists(LOCAL_CATALOG_PATH):
            with open(LOCAL_CATALOG_PATH, 'r') as f:
                return json.load(f)
        return []

    # Remote Mode (The Bridge)
    headers = {}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"

    try:
        resp = requests.get(CATALOG_URL, headers=headers, timeout=10)
        if resp.status_code == 200:
            return resp.json()
        else:
            print(f"Error fetching catalog: {resp.status_code} - {resp.text}")
            return []
    except Exception as e:
        print(f"Exception fetching catalog: {e}")
        return []

def get_item_by_id(item_id):
    catalog = get_catalog()
    for item in catalog:
        if item.get("id") == item_id:
            return item
    return None

@app.route("/")
def index():
    catalog = get_catalog()
    return render_template("index.html", catalog=catalog)

@app.route("/view/<item_id>")
def view_item(item_id):
    item = get_item_by_id(item_id)
    if not item:
        abort(404)
    return render_template("detail.html", item=item)

if __name__ == "__main__":
    # Local development server
    app.run(host="0.0.0.0", port=8080, debug=True)
