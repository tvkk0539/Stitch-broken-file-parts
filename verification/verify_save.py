from playwright.sync_api import sync_playwright, expect
import time
import random

def verify_save_account_id():
    unique_id = str(int(time.time())) + str(random.randint(100,999))
    wf_name = f"Test Save {unique_id}"
    acc_id = f"acc-{unique_id}"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        try:
            # 1. Open Automation
            page.goto("http://localhost:5000")
            page.click("div[data-view='automation']")

            # 2. Create Workflow
            page.click("text=+ Create Workflow")
            page.fill("#wf-editor-name", wf_name)

            # 3. Add GitHub Step
            page.click("text=+ Add Step")
            page.select_option("select.wf-step-type", "github_publish")

            # 4. Enter Account ID
            acc_input = page.locator(".wf-gh-acc-tokenizer input.tag-input")
            expect(acc_input).to_be_visible()
            acc_input.fill(acc_id)
            acc_input.press("Enter")

            # 5. Save
            page.click("text=💾 Save Workflow")
            time.sleep(1)

            # 6. Verify Persistence
            page.reload()
            page.click("div[data-view='automation']")

            # Find specific card
            # We use locator filtering to find the card with the specific text
            card = page.locator(".app-card").filter(has_text=wf_name)
            expect(card).to_be_visible()

            # Click Edit on THAT card
            card.locator("button").filter(has_text="✏️").click()

            # Check tokenizer
            expect(page.locator(".wf-gh-acc-tokenizer .tag-pill")).to_contain_text(acc_id)

            print(f"Verification Successful: Account ID {acc_id} preserved.")
            page.screenshot(path="verification/save_success_unique.png")

        except Exception as e:
            print(f"Verification Failed: {e}")
            page.screenshot(path="verification/save_fail_unique.png")
            raise e
        finally:
            browser.close()

if __name__ == "__main__":
    verify_save_account_id()
