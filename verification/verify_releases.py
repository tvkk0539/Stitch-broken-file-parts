
from playwright.sync_api import sync_playwright
import time

def verify_releases_ui():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 800})
        page = context.new_page()

        print("Navigating to Dashboard...")
        page.goto("http://localhost:5000")

        # Mock Accounts
        page.route("**/api/apps/github/accounts", lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body="[{\"id\": \"123\", \"username\": \"TestUser\", \"avatar_url\": \"\"}]"
        ))

        # Mock Repos (Empty to skip rendering grid)
        page.route("**/api/apps/github/user/repos*", lambda route: route.fulfill(
            status=200, content_type="application/json", body="[]"
        ))

        # Mock Releases (Multiple)
        releases_json = """[
            {
                "tag_name": "v2.0.0",
                "name": "Release 2.0",
                "published_at": "2023-10-01T12:00:00Z",
                "prerelease": false,
                "assets": [
                    {"name": "app-v2.zip", "size": 1024, "browser_download_url": "http://example.com/v2.zip"}
                ]
            },
            {
                "tag_name": "v1.5.0-beta",
                "name": "Beta 1.5",
                "published_at": "2023-09-01T12:00:00Z",
                "prerelease": true,
                "assets": [
                    {"name": "app-beta.zip", "size": 512, "browser_download_url": "http://example.com/beta.zip"}
                ]
            }
        ]"""
        page.route("**/api/apps/github/releases", lambda route: route.fulfill(
            status=200, content_type="application/json", body=releases_json
        ))

        print("Navigating to GitHub Manager...")
        page.click("div[data-view=\"apps\"]")
        page.click(".app-card:has-text(\"GitHub Manager\")")

        # Wait specifically for the Select button in the accounts grid
        # The selector was likely too broad before
        page.wait_for_selector("#gh-accounts-grid button:has-text(\"Select\")")
        page.click("#gh-accounts-grid button:has-text(\"Select\")")

        print("Switching to Downloader...")
        page.click("#gh-tab-down")

        print("Fetching Releases...")
        page.fill("#gh-repo-input", "user/repo")
        page.click("button:has-text(\"Fetch\")")

        print("Waiting for Release Cards...")
        page.wait_for_selector("text=v2.0.0")
        page.wait_for_selector("text=v1.5.0-beta")

        # Check Latest badge
        page.wait_for_selector("text=LATEST")

        # Check Prerelease badge
        page.wait_for_selector("text=PRE")

        page.screenshot(path="verification/07_releases_list.png")
        print("Captured Releases List.")

        browser.close()

if __name__ == "__main__":
    verify_releases_ui()
