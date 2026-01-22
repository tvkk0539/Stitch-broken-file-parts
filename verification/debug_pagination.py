
from playwright.sync_api import sync_playwright
import re
import json

def debug_pagination():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 800})

        page.on("console", lambda msg: print(f"CONSOLE: {msg.text}"))

        page.goto("http://localhost:5000")

        # Mock APIs
        page.route(re.compile(r".*/api/apps/github/accounts"), lambda route: route.fulfill(
            status=200, content_type="application/json", body="[{\"id\": \"123\", \"username\": \"TestUser\", \"avatar_url\": \"\"}]"
        ))
        page.route(re.compile(r".*/api/apps/github/user/repos"), lambda route: route.fulfill(
            status=200, content_type="application/json", body="[]"
        ))

        releases_page1 = []
        for i in range(30):
            releases_page1.append({
                "tag": f"v2.{30-i}.0", "name": f"Rel {30-i}", "published_at": "2023-01-01", "prerelease": False, "assets": []
            })

        page.route(re.compile(r".*/api/apps/github/releases"), lambda route: route.fulfill(
            status=200, content_type="application/json", body=json.dumps(releases_page1)
        ))

        page.click("div[data-view=\"apps\"]")
        page.click(".app-card:has-text(\"GitHub Manager\")")
        page.click("#gh-accounts-grid button:has-text(\"Select\")")
        page.click("#gh-tab-down")
        page.fill("#gh-repo-input", "user/repo")
        page.click("button:has-text(\"Fetch\")")

        try:
            page.wait_for_selector("text=Page 1", timeout=5000)
            print("Success: Page 1 found.")
        except Exception as e:
            print(f"Error: {e}")
            print(page.content())
            page.screenshot(path="verification/11_debug_fail.png")

        browser.close()

if __name__ == "__main__":
    debug_pagination()
