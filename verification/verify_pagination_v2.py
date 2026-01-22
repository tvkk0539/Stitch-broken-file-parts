
from playwright.sync_api import sync_playwright
import re
import json

def verify_pagination():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 800})

        # page.on("console", lambda msg: print(f"CONSOLE: {msg.text}"))

        page.goto("http://localhost:5000")

        # Mock APIs
        page.route(re.compile(r".*/api/apps/github/accounts"), lambda route: route.fulfill(
            status=200, content_type="application/json", body="[{\"id\": \"123\", \"username\": \"TestUser\", \"avatar_url\": \"\"}]"
        ))
        page.route(re.compile(r".*/api/apps/github/user/repos"), lambda route: route.fulfill(
            status=200, content_type="application/json", body="[]"
        ))

        releases_page1 = [{"tag": f"v2.{30-i}.0", "name": f"Rel {30-i}", "published_at": "2023-01-01", "prerelease": False, "assets": []} for i in range(30)]
        releases_page2 = [{"tag": f"v1.{5-i}.0", "name": f"Old {5-i}", "published_at": "2022-01-01", "prerelease": False, "assets": []} for i in range(5)]

        def handle_releases(route):
            try:
                # Flask calls requests.get which is server-side.
                # Playwright intercepts Browser -> Flask.
                # Flask returns what we mock here.
                # We need to read the "page" param from the Browser request payload.
                req_json = route.request.post_data_json or {}
                page_num = req_json.get("page", 1)

                print(f"Mocking response for Page {page_num}")
                if page_num == 1:
                    route.fulfill(status=200, content_type="application/json", body=json.dumps(releases_page1))
                elif page_num == 2:
                    route.fulfill(status=200, content_type="application/json", body=json.dumps(releases_page2))
                else:
                    route.fulfill(status=200, content_type="application/json", body="[]")
            except Exception as e:
                print(f"Mock Error: {e}")
                route.fulfill(status=500)

        page.route(re.compile(r".*/api/apps/github/releases"), handle_releases)

        page.click("div[data-view=\"apps\"]")
        page.click(".app-card:has-text(\"GitHub Manager\")")
        page.click("#gh-accounts-grid button:has-text(\"Select\")")
        page.click("#gh-tab-down")
        page.fill("#gh-repo-input", "user/repo")
        page.click("button:has-text(\"Fetch\")")

        page.wait_for_selector("text=Page 1")
        print("Page 1 loaded.")

        # Scroll to bottom to find Next button? No, click handles scrolling usually.
        # Check Next Button
        if page.is_visible("button:has-text(\"Next ➡️\")"):
            print("Next button visible.")
            page.click("button:has-text(\"Next ➡️\")")
        else:
            print("FAIL: Next button not found.")
            return

        page.wait_for_selector("text=Page 2")
        print("Page 2 loaded.")

        if page.is_visible("button:has-text(\"⬅️ Previous\")"):
            print("Previous button visible.")
        else:
            print("FAIL: Previous button not found.")

        page.screenshot(path="verification/11_pagination_pass.png")
        browser.close()

if __name__ == "__main__":
    verify_pagination()
