from playwright.sync_api import sync_playwright
import time
import requests
import os

BASE_URL = "http://localhost:5000"

def verify_github_editor():
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
            body='["main"]'
        ))

        # MOCK: Contents (Root) -> File
        page.route("**/api/apps/github/repo/contents", lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body='{"type":"dir", "items":[{"name":"README.md", "path":"README.md", "type":"file", "size":100, "sha":"def", "url":""}]}'
        ))

        page.goto(BASE_URL)
        page.click("div[data-view='apps']")
        time.sleep(1)
        page.click(".app-card >> text=GitHub Manager")
        time.sleep(1)
        page.click("button >> text=Select")
        time.sleep(1)

        # Open Browser
        page.click("button[title='Browse Code']")
        time.sleep(1)

        # MOCK: File Content (base64 "Hello World")
        # "Hello World" in base64 is "SGVsbG8gV29ybGQ="
        page.route("**/api/apps/github/repo/contents", lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body='{"type":"file", "name":"README.md", "path":"README.md", "size":11, "sha":"def", "content":"SGVsbG8gV29ybGQ=", "encoding":"base64"}'
        ))

        # Click File
        print("Clicking README.md...")
        page.click("text=README.md")
        time.sleep(1)

        # Verify Editor Modal
        assert page.is_visible("#gh-editor-modal")
        assert page.is_visible("#gh-editor-filename >> text=README.md")

        # Verify Content
        content = page.input_value("#gh-editor-content")
        print(f"File content in editor: {content}")
        assert content == "Hello World"

        print("Editor Verified ✅")
        page.screenshot(path="/home/jules/verification/github_editor_modal.png")

        browser.close()

if __name__ == "__main__":
    verify_github_editor()
