
from playwright.sync_api import sync_playwright

def verify_release_search():
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
        page.wait_for_selector("#gh-release-filter")

        print("Typing \"beta\"...")
        page.fill("#gh-release-filter", "beta")
        page.wait_for_timeout(1000)

        # Inspect HTML of the beta card
        # We find the element that contains the text
        beta_el = page.locator(".gh-release-card", has_text="v1.5.0-beta")

        if beta_el.count() > 0:
            style = beta_el.get_attribute("style")
            print(f"Beta Card Style: {style}")
            print(f"Is Visible: {beta_el.is_visible()}")
        else:
            print("Beta card element not found in DOM")

        browser.close()

if __name__ == "__main__":
    verify_release_search()
