from playwright.sync_api import sync_playwright, expect
import time
import requests
import os

BASE_URL = "http://localhost:5000"

def verify_logs_ui():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Capture Console Logs
        page.on("console", lambda msg: print(f"BROWSER LOG: {msg.text}"))
        page.on("pageerror", lambda exc: print(f"BROWSER ERROR: {exc}"))

        # MOCK: Jobs API
        page.route("**/api/jobs", lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body='{"running":[{"id":"job123", "name":"Mock Job", "details":{}}], "pending":[], "history":[]}'
        ))

        # MOCK: Logs Stream (System)
        page.route("**/api/logs", lambda route: route.fulfill(
            status=200,
            content_type="text/event-stream",
            body='data: [System] Connected\n\n'
        ))

        # MOCK: Logs Stream (Job)
        page.route("**/api/logs/job123", lambda route: route.fulfill(
            status=200,
            content_type="text/event-stream",
            body='data: [Job] Job Started\n\n'
        ))

        page.goto(BASE_URL)

        # Click Logs View
        page.click("div[data-view='logs']")

        # Wait for tab to appear (using web-first assertion)
        tab_locator = page.locator("button[data-id='job123']")
        expect(tab_locator).to_be_visible(timeout=5000)

        print("Tab found. HTML before click:")
        print(page.inner_html("#log-tabs-container"))

        # Click the tab
        print("Clicking tab...")
        tab_locator.click()

        # Wait for class to apply
        try:
            expect(tab_locator).to_have_class("log-tab active", timeout=2000)
            print("Tab has 'active' class ✅")
        except AssertionError:
            print("Tab FAILED to get 'active' class.")
            print("HTML after click:")
            print(page.inner_html("#log-tabs-container"))
            page.screenshot(path="/home/jules/verification/logs_ui_fail.png")
            raise

        print("Logs UI Verified ✅")
        browser.close()

if __name__ == "__main__":
    if not os.path.exists("/home/jules/verification"):
        os.makedirs("/home/jules/verification")
    verify_logs_ui()
