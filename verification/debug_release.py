
from playwright.sync_api import sync_playwright

def verify_releases_ui():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 800})

        # Capture Console Logs
        page.on("console", lambda msg: print(f"BROWSER CONSOLE: {msg.text}"))
        page.on("pageerror", lambda err: print(f"BROWSER ERROR: {err}"))

        print("Navigating to Dashboard...")
        page.goto("http://localhost:5000")

        # Mock Accounts
        page.route("**/api/apps/github/accounts", lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body="[{\"id\": \"123\", \"username\": \"TestUser\", \"avatar_url\": \"\"}]"
        ))

        # Mock Repos
        page.route("**/api/apps/github/user/repos*", lambda route: route.fulfill(
            status=200, content_type="application/json", body="[]"
        ))

        # Mock Releases
        releases_json = """[
            {
                "tag_name": "v2.0.0",
                "name": "Release 2.0",
                "published_at": "2023-10-01T12:00:00Z",
                "prerelease": false,
                "assets": [
                    {"name": "app-v2.zip", "size": 1024, "browser_download_url": "http://example.com/v2.zip"}
                ]
            }
        ]"""
        page.route("**/api/apps/github/releases", lambda route: route.fulfill(
            status=200, content_type="application/json", body=releases_json
        ))

        print("Navigating...")
        page.click("div[data-view=\"apps\"]")
        page.click(".app-card:has-text(\"GitHub Manager\")")

        # Select Account
        page.wait_for_selector("#gh-accounts-grid button:has-text(\"Select\")")
        page.click("#gh-accounts-grid button:has-text(\"Select\")")

        # Downloader Tab
        page.click("#gh-tab-down")

        # Fetch
        page.fill("#gh-repo-input", "user/repo")
        page.click("button:has-text(\"Fetch\")")

        print("Waiting for v2.0.0...")
        try:
            page.wait_for_selector("text=v2.0.0", timeout=5000)
            print("Found v2.0.0")
            page.screenshot(path="verification/07_releases_list.png")
            print("Success.")
        except Exception as e:
            print(f"Timeout! Content: {page.content()}")
            page.screenshot(path="verification/07_fail.png")

        browser.close()

if __name__ == "__main__":
    verify_releases_ui()
