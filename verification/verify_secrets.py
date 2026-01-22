
from playwright.sync_api import sync_playwright
import re
import json

def verify_secrets_ui():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        page.on("dialog", lambda dialog: dialog.accept())

        page.goto("http://localhost:5000")

        # Mock APIs
        page.route(re.compile(r".*/api/apps/github/accounts"), lambda route: route.fulfill(
            status=200, content_type="application/json", body="[{\"id\": \"123\", \"username\": \"TestUser\", \"avatar_url\": \"\"}]"
        ))

        repos_json = """[{"name": "user/repo", "private": false, "stars": 0, "updated_at": "2023-01-01"}]"""
        page.route(re.compile(r".*/api/apps/github/user/repos"), lambda route: route.fulfill(
            status=200, content_type="application/json", body=repos_json
        ))

        # Mock Secrets List
        secrets_json = """{"total_count": 1, "secrets": [{"name": "MY_API_KEY", "updated_at": "2023-01-01"}]}"""
        page.route(re.compile(r".*/api/apps/github/secrets/list"), lambda route: route.fulfill(
            status=200, content_type="application/json", body=secrets_json
        ))

        # Setup
        page.click("div[data-view=\"apps\"]")
        page.click(".app-card:has-text(\"GitHub Manager\")")
        page.click("#gh-accounts-grid button:has-text(\"Select\")")

        # Check Secrets Button (Key Icon)
        # title="Secrets"
        page.wait_for_selector("button[title=\"Secrets\"]")
        print("Secrets button visible.")

        page.click("button[title=\"Secrets\"]")
        page.wait_for_selector("#gh-secrets-modal", state="visible")
        print("Secrets modal opened.")

        # Check List
        page.wait_for_selector("text=MY_API_KEY")
        print("Secret listed.")

        # Check Add Flow (Mock Put)
        page.route("**/api/apps/github/secrets/put", lambda route: route.fulfill(
            status=200, content_type="application/json", body="{\"status\": \"success\"}"
        ))

        page.fill("#gh-secret-name", "NEW_SECRET")
        page.fill("#gh-secret-value", "super_secret")
        page.click("button:has-text(\"Save Secret\")")

        # Check Toast? Or just assume success if no alert.
        # Ideally, we should wait for toast.

        page.screenshot(path="verification/15_secrets_ui.png")
        browser.close()

if __name__ == "__main__":
    verify_secrets_ui()
