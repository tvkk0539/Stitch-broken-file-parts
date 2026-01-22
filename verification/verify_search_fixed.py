
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

        # Corrected Mock Schema (tag instead of tag_name)
        releases_json = """[
            {
                "tag": "v2.0.0", "name": "Stable", "published_at": "2023-10-01", "prerelease": false,
                "assets": [{"name": "app-v2.zip", "size": 1024, "browser_download_url": ""}]
            },
            {
                "tag": "v1.5.0-beta", "name": "Beta", "published_at": "2023-09-01", "prerelease": true,
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

        try:
            page.wait_for_selector("#gh-release-filter", timeout=5000)
            print("Search bar visible.")
        except:
            print("Search bar NOT visible.")
            browser.close()
            return

        # --- Test 1: Tag Filter ---
        print("Typing \"beta\"...")
        page.fill("#gh-release-filter", "beta")
        page.wait_for_timeout(500)

        beta_vis = page.locator("text=v1.5.0-beta").is_visible()
        stable_vis = page.locator("text=v2.0.0").is_visible()

        if beta_vis and not stable_vis:
            print("PASS: Filtered by Tag/Name correctly.")
        else:
            print(f"FAIL: Tag filter logic. Beta: {beta_vis}, Stable: {stable_vis}")

        # --- Test 2: Asset Filter ---
        print("Typing \"zip\"...")
        page.fill("#gh-release-filter", "zip")
        page.wait_for_timeout(500)

        # Both headers should be visible
        v2_vis = page.locator("text=v2.0.0").is_visible()
        v1_vis = page.locator("text=v1.5.0-beta").is_visible()

        # Assets should be visible (expanded)
        asset_v2_vis = page.locator("text=app-v2.zip").is_visible()
        asset_v1_vis = page.locator("text=app-beta.zip").is_visible()

        if v2_vis and v1_vis and asset_v2_vis and asset_v1_vis:
             print("PASS: Asset search auto-expanded cards.")
        else:
             print(f"FAIL: Asset search expansion. v2:{v2_vis}, v1:{v1_vis}, av2:{asset_v2_vis}, av1:{asset_v1_vis}")

        page.screenshot(path="verification/10_search_success_fixed.png")
        browser.close()

if __name__ == "__main__":
    verify_release_search()
