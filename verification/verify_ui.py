from playwright.sync_api import sync_playwright, expect
import time

def verify_automation_ui():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        try:
            # Navigate to Automation
            page.goto("http://localhost:5000")
            page.click("div[data-view='automation']")

            # Open Editor
            page.click("text=+ Create Workflow")

            # Add Step
            page.click("text=+ Add Step")

            # Select GitHub Publish
            page.select_option("select.wf-step-type", "github_publish")

            # Verify "Obfuscate Title" Checkbox exists
            checkbox = page.locator("input.wf-gh-obf-title")
            expect(checkbox).to_be_visible()
            expect(checkbox).to_be_checked() # Should be checked by default

            # Verify Camouflage exists
            camo = page.locator("input.wf-opt-camo")
            expect(camo).to_be_visible()

            # Uncheck it to verify interaction
            checkbox.uncheck()
            expect(checkbox).not_to_be_checked()

            # Screenshot
            page.screenshot(path="verification/automation_ui_verify_v3.png")
            print("Verification Successful: Checkbox found and interactive.")

        except Exception as e:
            print(f"Verification Failed: {e}")
            page.screenshot(path="verification/automation_ui_fail.png")
            raise e
        finally:
            browser.close()

if __name__ == "__main__":
    verify_automation_ui()
