
from playwright.sync_api import sync_playwright

def dump_html():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 800})

        # Capture Console
        page.on("console", lambda msg: print(f"CONSOLE: {msg.text}"))

        page.goto("http://localhost:5000")

        # Mock APIs
        page.route("**/api/apps/github/accounts", lambda route: route.fulfill(
            status=200, content_type="application/json", body="[{\"id\": \"123\", \"username\": \"TestUser\", \"avatar_url\": \"\"}]"
        ))
        page.route("**/api/apps/github/user/repos*", lambda route: route.fulfill(
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
        page.route("**/api/apps/github/releases", lambda route: route.fulfill(
            status=200, content_type="application/json", body=releases_json
        ))

        page.click("div[data-view=\"apps\"]")
        page.click(".app-card:has-text(\"GitHub Manager\")")
        page.wait_for_selector("#gh-accounts-grid button:has-text(\"Select\")")
        page.click("#gh-accounts-grid button:has-text(\"Select\")")
        page.click("#gh-tab-down")
        page.fill("#gh-repo-input", "user/repo")
        page.click("button:has-text(\"Fetch\")")

        print("Waiting for results...")
        try:
            page.wait_for_selector("#gh-release-filter", timeout=5000)
            print("Filter bar found.")
            # Wait a bit for render
            page.wait_for_timeout(1000)

            content = page.content()
            # print snippet of results
            if "v2.0.0" in content:
                print("Found v2.0.0 in HTML")
            else:
                print("v2.0.0 NOT in HTML")

            if "v1.5.0-beta" in content:
                print("Found v1.5.0-beta in HTML")
            else:
                print("v1.5.0-beta NOT in HTML")

        except Exception as e:
            print(f"Error waiting: {e}")

        browser.close()

if __name__ == "__main__":
    dump_html()
