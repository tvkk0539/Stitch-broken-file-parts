
from playwright.sync_api import sync_playwright
import re
import json

def verify_publisher_fetch():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        page.on("dialog", lambda dialog: dialog.accept())

        page.goto("http://localhost:5000")

        # Mock APIs
        page.route(re.compile(r".*/api/apps/github/accounts"), lambda route: route.fulfill(
            status=200, content_type="application/json", body="[{\"id\": \"123\", \"username\": \"TestUser\", \"avatar_url\": \"\"}]"
        ))
        page.route(re.compile(r".*/api/apps/github/user/repos"), lambda route: route.fulfill(
            status=200, content_type="application/json", body="[]"
        ))

        # Mock Releases
        releases_json = """[
            {
                "tag": "v1.0.0", "name": "Stable", "published_at": "2023-01-01", "prerelease": false, "assets": []
            }
        ]"""
        page.route(re.compile(r".*/api/apps/github/releases"), lambda route: route.fulfill(
            status=200, content_type="application/json", body=releases_json
        ))

        # Setup
        page.click("div[data-view=\"apps\"]")
        page.click(".app-card:has-text(\"GitHub Manager\")")
        page.click("#gh-accounts-grid button:has-text(\"Select\")")

        # Switch to Publisher
        page.click("#gh-tab-pub")

        # Check Fetch UI
        page.wait_for_selector("#gh-pub-repo-fetch")
        print("Fetch UI visible.")

        # Type Repo and Fetch
        page.fill("#gh-pub-repo-fetch", "user/repo")
        page.click("button:has-text(\"Fetch Releases\")")

        # Wait for results
        page.wait_for_selector("text=v1.0.0")
        print("Releases fetched.")

        # Click Select
        page.click("button:has-text(\"Select\")")

        # Check if Tag input is filled
        tag_val = page.input_value("#gh-pub-tag")
        if tag_val == "v1.0.0":
            print(f"PASS: Tag auto-filled with {tag_val}")
        else:
            print(f"FAIL: Tag input is {tag_val}")

        page.screenshot(path="verification/14_publisher_fetch.png")
        browser.close()

if __name__ == "__main__":
    verify_publisher_fetch()
