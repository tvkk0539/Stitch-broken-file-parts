
from playwright.sync_api import sync_playwright
import re

def verify_release_search():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 800})

        page.goto("http://localhost:5000")

        # Mock APIs
        page.route(re.compile(r".*/api/apps/github/accounts"), lambda route: route.fulfill(
            status=200, content_type="application/json", body="[{\"id\": \"123\", \"username\": \"TestUser\", \"avatar_url\": \"\"}]"
        ))
        page.route(re.compile(r".*/api/apps/github/user/repos"), lambda route: route.fulfill(
            status=200, content_type="application/json", body="[]"
        ))

        releases_json = """[
            {
                "tag_name": "v2.0.0", "name": "Stable", "published_at": "2023-10-01", "prerelease": false,
                "assets": [{"name": "app-v2.zip", "size": 1024, "browser_download_url": ""}]
            },
            {
                "tag_name": "v1.5.0-beta", "name": "Beta", "published_at": "2023-09-01", "prerelease": true,
                "assets": [{"name": "app-beta.zip", "size": 512, "browser_download_url": ""}]
            }
        ]"""
        page.route(re.compile(r".*/api/apps/github/releases"), lambda route: route.fulfill(
            status=200, content_type="application/json", body=releases_json
        ))

        # Setup
        page.click("div[data-view=\"apps\"]")
        page.click(".app-card:has-text(\"GitHub Manager\")")
        page.wait_for_selector("#gh-accounts-grid button:has-text(\"Select\")")
        page.click("#gh-accounts-grid button:has-text(\"Select\")")
        page.click("#gh-tab-down")
        page.fill("#gh-repo-input", "user/repo")
        page.click("button:has-text(\"Fetch\")")

        page.wait_for_selector("#gh-release-filter")
        page.screenshot(path="verification/step1_initial.png")

        # Verify initial state
        if page.is_visible("text=v2.0.0"):
            print("Initial: v2.0.0 visible.")
        else:
            print("Initial: v2.0.0 HIDDEN.")

        # --- Test 1: Tag Filter ---
        print("Typing \"beta\"...")
        page.fill("#gh-release-filter", "beta")
        page.wait_for_timeout(1000)
        page.screenshot(path="verification/step2_beta.png")

        beta_vis = page.locator("text=v1.5.0-beta").is_visible()
        stable_vis = page.locator("text=v2.0.0").is_visible()

        print(f"Beta Vis: {beta_vis}, Stable Vis: {stable_vis}")

        browser.close()

if __name__ == "__main__":
    verify_release_search()
