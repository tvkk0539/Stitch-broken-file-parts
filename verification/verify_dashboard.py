from playwright.sync_api import sync_playwright

def verify_ui():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        try:
            # Go to the app
            page.goto("http://localhost:5000")

            # Wait for key elements to ensure loading
            page.wait_for_selector("#sidebar")
            page.wait_for_selector("#views-container")

            # Take a screenshot of the Files view (default)
            page.screenshot(path="verification/dashboard.png")
            print("Screenshot saved to verification/dashboard.png")

        except Exception as e:
            print(f"Error: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    verify_ui()
