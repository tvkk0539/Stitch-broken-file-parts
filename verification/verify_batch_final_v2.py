
from playwright.sync_api import sync_playwright
import re
import json

def verify_batch_download():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 800})

        page.on("dialog", lambda dialog: dialog.accept("Downloads/TestBatch/"))

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
                "tag": "v1.0.0", "name": "Rel 1", "published_at": "2023-01-01", "prerelease": false,
                "assets": [
                    {"name": "file1.zip", "size": 100, "download_url": "http://x/1"},
                    {"name": "file2.zip", "size": 200, "download_url": "http://x/2"},
                    {"name": "file3.zip", "size": 300, "download_url": "http://x/3"}
                ]
            }
        ]"""
        page.route(re.compile(r".*/api/apps/github/releases"), lambda route: route.fulfill(
            status=200, content_type="application/json", body=releases_json
        ))

        page.click("div[data-view=\"apps\"]")
        page.click(".app-card:has-text(\"GitHub Manager\")")
        page.click("#gh-accounts-grid button:has-text(\"Select\")")
        page.click("#gh-tab-down")
        page.fill("#gh-repo-input", "user/repo")
        page.click("button:has-text(\"Fetch\")")

        page.wait_for_selector("text=v1.0.0")

        btn = page.locator("button:has-text(\"Download All\")")
        if btn.is_visible():
            print("Download All button visible.")

        def handle_batch(route):
            data = route.request.post_data_json
            print(f"Batch Request: {len(data[assets])} items to {data[path]}")
            if len(data[assets]) == 3 and data[path] == "Downloads/TestBatch/":
                print("PASS: Correct payload.")
                route.fulfill(status=200, content_type="application/json", body="{\"status\": \"queued\"}")
            else:
                print("FAIL: Incorrect payload.")
                route.abort()

        page.route("**/api/apps/github/download/batch", handle_batch)

        btn.click()
        page.wait_for_timeout(1000)

        page.screenshot(path="verification/12_batch_download_success.png")
        browser.close()

if __name__ == "__main__":
    verify_batch_download()
