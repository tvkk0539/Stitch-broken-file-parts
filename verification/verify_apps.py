from playwright.sync_api import sync_playwright
import time

def verify_apps_ui():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        try:
            # 1. Dashboard
            page.goto("http://localhost:5000")
            page.wait_for_selector("#sidebar")

            # 2. Click Apps Icon (Wait for it to be visible first)
            # Use a robust selector for the icon we added
            page.wait_for_selector("div.nav-item[onclick=\"switchView('apps')\"]")
            page.click("div.nav-item[onclick=\"switchView('apps')\"]")

            # 3. Wait for Apps Grid
            page.wait_for_selector("#apps-grid")
            time.sleep(0.5) # Allow transition
            page.screenshot(path="verification/apps_grid.png")
            print("Apps Grid Screenshot Saved")

            # 4. Click GitHub App
            page.click(".app-card:has-text('GitHub Manager')")

            # 5. Wait for GitHub View
            page.wait_for_selector("#view-gh-app")
            time.sleep(0.5)
            page.screenshot(path="verification/github_app.png")
            print("GitHub App Screenshot Saved")

        except Exception as e:
            print(f"Error: {e}")
            # Take screenshot on error to debug
            page.screenshot(path="verification/error.png")
        finally:
            browser.close()

if __name__ == "__main__":
    verify_apps_ui()
