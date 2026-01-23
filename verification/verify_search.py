
from playwright.sync_api import sync_playwright

def verify_release_search():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 800})

        print("Navigating to Dashboard...")
        page.goto("http://localhost:5000")

        # Mock APIs
        page.route("**/api/apps/github/accounts", lambda route: route.fulfill(
            status=200, content_type="application/json", body="[{\"id\": \"123\", \"username\": \"TestUser\", \"avatar_url\": \"\"}]"
        ))
        page.route("**/api/apps/github/user/repos*", lambda route: route.fulfill(
            status=200, content_type="application/json", body="[]"
        ))

        # Mock Releases with distinctive names
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
        page.route("**/api/apps/github/releases", lambda route: route.fulfill(
            status=200, content_type="application/json", body=releases_json
        ))

        # Login flow
        page.click("div[data-view=\"apps\"]")
        page.click(".app-card:has-text(\"GitHub Manager\")")
        page.wait_for_selector("#gh-accounts-grid button:has-text(\"Select\")")
        page.click("#gh-accounts-grid button:has-text(\"Select\")")

        # Fetch
        page.click("#gh-tab-down")
        page.fill("#gh-repo-input", "user/repo")
        page.click("button:has-text(\"Fetch\")")

        # Wait for results
        page.wait_for_selector("#gh-release-filter")
        print("Search Bar Visible.")

        # Test 1: Search for "beta" (should hide v2.0.0)
        print("Typing \"beta\"...")
        page.fill("#gh-release-filter", "beta")

        # Expect v1.5.0 visible, v2.0.0 hidden
        # Note: visibility check in playwright checks CSS display property too
        if page.is_visible("text=v1.5.0-beta") and not page.is_visible("text=v2.0.0"):
            print("PASS: Filtered by Tag/Name correctly.")
        else:
            print("FAIL: Tag filter logic.")

        # Test 2: Search for "zip" (should show both assets)
        print("Typing \"zip\"...")
        page.fill("#gh-release-filter", "zip")

        # Both cards should be visible AND expanded (assets visible)
        if page.is_visible("text=app-v2.zip") and page.is_visible("text=app-beta.zip"):
             print("PASS: Asset search auto-expanded cards.")
        else:
             print("FAIL: Asset search expansion.")

        page.screenshot(path="verification/08_search_filter.png")
        browser.close()

if __name__ == "__main__":
    verify_release_search()
