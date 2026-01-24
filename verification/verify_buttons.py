from playwright.sync_api import sync_playwright
import time
import requests

def verify_buttons():
    # Ensure items exist
    try:
        requests.post("http://localhost:5000/api/catalog", json={
            "title": "Button Test Item",
            "file_name": "test.mkv",
            "size_bytes": 123456,
            "url": "http://test.com",
            "category": "Test",
            "assets": [{"url": "http://test.com/1"}]
        })
    except: pass

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.goto("http://localhost:5000")
        page.click("div[data-view='catalog']")
        time.sleep(2)

        # Click first item
        page.click(".catalog-card")
        time.sleep(1)

        # Screenshot to check buttons
        page.screenshot(path="/home/jules/verification/catalog_buttons.png")
        print("Screenshot taken.")
        browser.close()

if __name__ == "__main__":
    verify_buttons()
