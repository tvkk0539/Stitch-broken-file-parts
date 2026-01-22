
from playwright.sync_api import sync_playwright
import time

def verify_ui():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 800})
        page = context.new_page()

        print("Navigating to Dashboard...")
        page.goto("http://localhost:5000")
        page.wait_for_selector("#file-list")
        page.screenshot(path="verification/01_dashboard.png")
        print("Captured Dashboard.")

        print("Navigating to Apps...")
        page.click("div[data-view=\"apps\"]")
        page.wait_for_selector(".app-card")
        page.screenshot(path="verification/02_apps.png")
        print("Captured Apps.")

        print("Navigating to GitHub Manager...")
        page.click(".app-card:has-text(\"GitHub Manager\")")
        page.wait_for_selector("#gh-state-accounts")
        page.screenshot(path="verification/03_github_accounts.png")
        print("Captured GitHub Accounts.")

        print("Opening Login Modal...")
        page.click("button:has-text(\"+ Add Account\")")
        page.wait_for_selector("#gh-login-modal", state="visible")
        page.screenshot(path="verification/04_github_login.png")
        print("Captured Login Modal.")

        browser.close()

if __name__ == "__main__":
    verify_ui()
