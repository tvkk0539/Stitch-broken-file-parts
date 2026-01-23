from playwright.sync_api import sync_playwright
import time
import os

def check_ui():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={'width': 1280, 'height': 800})
        page = context.new_page()

        print("Navigating to home...")
        page.goto("http://127.0.0.1:5000")
        page.wait_for_selector("#sidebar") # Wait for sidebar

        # Files View (Default)
        print("Capturing Files view...")
        time.sleep(1)
        page.screenshot(path="verification/1_files.png")

        # Queue View
        print("Capturing Queue view...")
        page.click('[data-view="queue"]')
        time.sleep(0.5)
        page.screenshot(path="verification/2_queue.png")

        # Apps View
        print("Capturing Apps view...")
        page.click('[data-view="apps"]')
        time.sleep(0.5)
        page.screenshot(path="verification/3_apps.png")

        # GitHub App
        print("Capturing GitHub App...")
        page.click('.app-card') # Click the GitHub card
        time.sleep(1) # Wait for accounts to load
        page.screenshot(path="verification/4_github_app.png")

        # Back to Apps
        page.click('[data-view="apps"]')

        # Logs View
        print("Capturing Logs view...")
        page.click('[data-view="logs"]')
        time.sleep(0.5)
        page.screenshot(path="verification/5_logs.png")

        # Settings View
        print("Capturing Settings view...")
        page.click('[data-view="settings"]')
        time.sleep(0.5)
        page.screenshot(path="verification/6_settings.png")

        browser.close()
        print("Done.")

if __name__ == "__main__":
    check_ui()
