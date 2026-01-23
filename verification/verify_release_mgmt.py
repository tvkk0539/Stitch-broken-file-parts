
from playwright.sync_api import sync_playwright
import re
import json

def verify_release_mgmt():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 800})

        # Override window.confirm to always accept
        page.on("dialog", lambda dialog: dialog.accept())

        page.goto("http://localhost:5000")

        # Mock APIs
        page.route(re.compile(r".*/api/apps/github/accounts"), lambda route: route.fulfill(
            status=200, content_type="application/json", body="[{\"id\": \"123\", \"username\": \"TestUser\", \"avatar_url\": \"\"}]"
        ))
        page.route(re.compile(r".*/api/apps/github/user/repos"), lambda route: route.fulfill(
            status=200, content_type="application/json", body="[]"
        ))

        # Mock Release with 1 asset
        releases_json = """[
            {
                "id": 999, "tag": "v1.0.0", "name": "Rel 1", "published_at": "2023-01-01", "prerelease": false,
                "assets": [
                    {"id": 101, "name": "file1.zip", "size": 100, "download_url": "http://x/1"}
                ]
            }
        ]"""
        page.route(re.compile(r".*/api/apps/github/releases"), lambda route: route.fulfill(
            status=200, content_type="application/json", body=releases_json
        ))

        # Setup
        page.click("div[data-view=\"apps\"]")
        page.click(".app-card:has-text(\"GitHub Manager\")")
        page.click("#gh-accounts-grid button:has-text(\"Select\")")
        page.click("#gh-tab-down")
        page.fill("#gh-repo-input", "user/repo")
        page.click("button:has-text(\"Fetch\")")

        page.wait_for_selector("text=v1.0.0")

        # Check Delete Release Button
        if page.is_visible("button:has-text(\"Del Release\")"):
            print("Delete Release button visible.")
        else:
            print("FAIL: Delete Release button missing.")

        # Check Trash All Button
        if page.is_visible("button:has-text(\"Trash All\")"):
            print("Trash All button visible.")
        else:
            print("FAIL: Trash All button missing.")

        # Expand to see asset delete button
        page.click(".arrow-icon") # Header click
        page.wait_for_timeout(500)

        # Check Asset Delete Button (Trash Icon)
        # We look for the button with title="Delete"
        del_asset_btn = page.locator("button[title=\"Delete\"]")
        if del_asset_btn.is_visible():
            print("Asset Delete button visible.")
        else:
            print("FAIL: Asset Delete button missing.")

        # Test Click Delete Release
        def handle_delete(route):
            print("Intercepted Delete Release")
            route.fulfill(status=200, content_type="application/json", body="{\"status\": \"deleted\"}")

        page.route("**/api/apps/github/release/delete", handle_delete)

        page.click("button:has-text(\"Del Release\")")
        page.wait_for_timeout(1000)

        page.screenshot(path="verification/13_release_mgmt.png")
        browser.close()

if __name__ == "__main__":
    verify_release_mgmt()
