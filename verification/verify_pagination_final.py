
from playwright.sync_api import sync_playwright
import re
import json

def verify_pagination():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 800})

        page.goto("http://localhost:5000")

        # Mock Accounts
        page.route(re.compile(r".*/api/apps/github/accounts"), lambda route: route.fulfill(
            status=200, content_type="application/json", body="[{\"id\": \"123\", \"username\": \"TestUser\", \"avatar_url\": \"\"}]"
        ))
        page.route(re.compile(r".*/api/apps/github/user/repos"), lambda route: route.fulfill(
            status=200, content_type="application/json", body="[]"
        ))

        # Mock Releases (Flask Schema: "tag", not "tag_name")
        # Page 1: 30 items
        releases_page1 = []
        for i in range(30):
            releases_page1.append({
                "tag": f"v2.{30-i}.0", "name": f"Rel {30-i}", "published_at": "2023-01-01", "prerelease": False, "assets": []
            })

        # Page 2: 5 items
        releases_page2 = []
        for i in range(5):
            releases_page2.append({
                "tag": f"v1.{5-i}.0", "name": f"Old {5-i}", "published_at": "2022-01-01", "prerelease": False, "assets": []
            })

        def handle_releases(route):
            try:
                post_data = route.request.post_data_json
                page_num = post_data.get("page", 1)
                print(f"Intercepted Request for Page: {page_num}")

                if page_num == 1:
                    route.fulfill(status=200, content_type="application/json", body=json.dumps(releases_page1))
                elif page_num == 2:
                    route.fulfill(status=200, content_type="application/json", body=json.dumps(releases_page2))
                else:
                    route.fulfill(status=200, content_type="application/json", body="[]")
            except Exception as e:
                print(f"Mock Error: {e}")
                route.fulfill(status=500, body=str(e))

        page.route(re.compile(r".*/api/apps/github/releases"), handle_releases)

        # Setup
        page.click("div[data-view=\"apps\"]")
        page.click(".app-card:has-text(\"GitHub Manager\")")
        page.wait_for_selector("#gh-accounts-grid button:has-text(\"Select\")")
        page.click("#gh-accounts-grid button:has-text(\"Select\")")
        page.click("#gh-tab-down")
        page.fill("#gh-repo-input", "user/repo")
        page.click("button:has-text(\"Fetch\")")

        # Check Page 1
        page.wait_for_selector("text=Page 1")
        page.wait_for_selector("text=v2.30.0")

        if page.is_visible("text=Next ➡️"):
            print("Page 1: Next button visible.")
        else:
            print("FAIL: Page 1 Next button missing.")

        # Click Next
        page.click("text=Next ➡️")

        # Check Page 2
        page.wait_for_selector("text=Page 2")
        page.wait_for_selector("text=v1.5.0")

        if page.is_visible("text=⬅️ Previous"):
            print("Page 2: Previous button visible.")
        else:
            print("FAIL: Page 2 Previous button missing.")

        if not page.is_visible("text=Next ➡️"):
            print("Page 2: Next button correctly hidden.")
        else:
            print("FAIL: Page 2 Next button visible (should be hidden).")

        page.screenshot(path="verification/11_pagination_final.png")
        browser.close()

if __name__ == "__main__":
    verify_pagination()
