
from playwright.sync_api import sync_playwright
import time

def verify_import_ui():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 800})
        page = context.new_page()

        print("Navigating to Dashboard...")
        page.goto("http://localhost:5000")

        # Mocking the account response since we can't login effectively without a real token
        # However, the user flow requires clicking through the UI.
        # I will inject a "mock" account into the frontend state via console if possible,
        # OR simpler: I will manually open the "My Repos" view by manipulating the DOM or state if I can.
        # But wait, the previous verification showed the Login Modal.
        # To see "My Repos", I need to be "logged in".
        # I can mock the API response for /api/apps/github/accounts to return a fake account.

        # Intercept Accounts API
        page.route("**/api/apps/github/accounts", lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body="[{\"id\": \"123\", \"username\": \"TestUser\", \"avatar_url\": \"\"}]"
        ))

        # Intercept User Repos API
        page.route("**/api/apps/github/user/repos*", lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body="[]" # Empty repos, so we should see just the New and Import buttons
        ))

        print("Navigating to Apps -> GitHub...")
        page.click("div[data-view=\"apps\"]")
        page.click(".app-card:has-text(\"GitHub Manager\")")

        print("Selecting Fake Account...")
        # Since we mocked the API, the account list should show "TestUser"
        page.wait_for_selector("text=TestUser")
        page.click("button:has-text(\"Select\")")

        print("Waiting for My Repos Grid...")
        page.wait_for_selector("#gh-view-repos")

        # Take screenshot of grid with Import Button
        page.wait_for_selector("text=Import Repo")
        page.screenshot(path="verification/05_import_button.png")
        print("Captured Import Button.")

        print("Opening Import Modal...")
        page.click("text=Import Repo")
        page.wait_for_selector("#gh-import-repo-modal", state="visible")
        page.screenshot(path="verification/06_import_modal.png")
        print("Captured Import Modal.")

        browser.close()

if __name__ == "__main__":
    verify_import_ui()
