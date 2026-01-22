
from playwright.sync_api import sync_playwright
import re
import json

def verify_repo_search():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 800})

        page.goto("http://localhost:5000")

        # Mock Accounts
        page.route(re.compile(r".*/api/apps/github/accounts"), lambda route: route.fulfill(
            status=200, content_type="application/json", body="[{\"id\": \"123\", \"username\": \"TestUser\", \"avatar_url\": \"\"}]"
        ))

        # Mock Repos
        repos_json = json.dumps([
            {"name": "user/my-awesome-project", "private": False, "stars": 10, "updated_at": "2023-01-01"},
            {"name": "user/secret-stuff", "private": True, "stars": 0, "updated_at": "2023-01-01"},
            {"name": "user/another-public-repo", "private": False, "stars": 5, "updated_at": "2023-01-01"}
        ])
        page.route(re.compile(r".*/api/apps/github/user/repos"), lambda route: route.fulfill(
            status=200, content_type="application/json", body=repos_json
        ))

        # Setup
        page.click("div[data-view=\"apps\"]")
        page.click(".app-card:has-text(\"GitHub Manager\")")
        page.click("#gh-accounts-grid button:has-text(\"Select\")")

        page.wait_for_selector("#gh-repos-filter")
        print("Search bar visible.")

        # Initial check
        if page.is_visible("text=my-awesome-project") and page.is_visible("text=secret-stuff"):
            print("Initial: All repos visible.")
        else:
            print("FAIL: Initial repos missing.")

        # Filter "secret"
        print("Typing \"secret\"...")
        page.fill("#gh-repos-filter", "secret")
        page.wait_for_timeout(500)

        secret_vis = page.is_visible("text=secret-stuff")
        awesome_vis = page.is_visible("text=my-awesome-project")

        if secret_vis and not awesome_vis:
            print("PASS: Filter logic works.")
        else:
            print(f"FAIL: Filter logic. Secret: {secret_vis}, Awesome: {awesome_vis}")

        page.screenshot(path="verification/13_repo_search.png")
        browser.close()

if __name__ == "__main__":
    verify_repo_search()
