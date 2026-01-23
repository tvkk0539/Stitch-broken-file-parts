from playwright.sync_api import sync_playwright
import time
import requests
import os

BASE_URL = "http://localhost:5000"

def verify_github_browser():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # MOCK: Accounts
        page.route("**/api/apps/github/accounts", lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body='[{"id":"1", "username":"testuser", "avatar_url":"", "name":"Test User"}]'
        ))

        # MOCK: User Repos
        page.route("**/api/apps/github/user/repos*", lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body='[{"name":"testuser/test-repo", "private":false, "stars":0, "updated_at":"2023-01-01", "html_url":""}]'
        ))

        # MOCK: Branches
        page.route("**/api/apps/github/repo/branches", lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body='["main", "dev"]'
        ))

        # MOCK: Contents (Root)
        page.route("**/api/apps/github/repo/contents", lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body='{"type":"dir", "items":[{"name":"src", "path":"src", "type":"dir", "size":0, "sha":"abc", "url":""}, {"name":"README.md", "path":"README.md", "type":"file", "size":100, "sha":"def", "url":""}]}'
        ))

        page.on("console", lambda msg: print(f"PAGE LOG: {msg.text}"))
        page.on("pageerror", lambda err: print(f"PAGE ERROR: {err}"))

        page.goto(BASE_URL)
        page.click("div[data-view='apps']")
        time.sleep(1)

        page.click(".app-card >> text=GitHub Manager")
        time.sleep(1)

        page.click("button >> text=Select")
        time.sleep(1)

        # Check if button exists
        if page.is_visible("button[title='Browse Code']"):
            print("Button found!")
            page.click("button[title='Browse Code']")
        else:
            print("Button NOT found!")
            page.screenshot(path="/home/jules/verification/debug_no_button.png")

        time.sleep(1)

        # Screenshot state
        page.screenshot(path="/home/jules/verification/debug_modal_state.png")

        # Verify Browser Modal
        if not page.is_visible("#gh-browser-modal"):
             print("Modal is hidden. Checking CSS display...")
             display = page.eval_on_selector("#gh-browser-modal", "e => e.style.display")
             print(f"Modal Display: {display}")

        assert page.is_visible("#gh-browser-modal")
        assert page.is_visible("#gh-browser-title >> text=testuser/test-repo")

        assert page.input_value("#gh-browser-branch") == "main"
        assert page.is_visible("text=src")

        print("Browser Modal Verified ✅")

        browser.close()

if __name__ == "__main__":
    if not os.path.exists("/home/jules/verification"):
        os.makedirs("/home/jules/verification")
    verify_github_browser()
