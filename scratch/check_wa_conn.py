import os
import sys
import time
from playwright.sync_api import sync_playwright

def main():
    with sync_playwright() as p:
        user_data_dir = os.path.expanduser("~/.config/antigravity-chrome-data")
        browser = p.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=False,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            args=["--disable-gpu", "--no-sandbox", "--disable-dev-shm-usage"]
        )
        page = browser.pages[0] if browser.pages else browser.new_page()
        page.goto("https://web.whatsapp.com")
        print("Navigated to WhatsApp Web. Waiting for chat UI sync...")
        
        # Wait up to 45 seconds for chat UI to load
        for i in range(15):
            time.sleep(3)
            if page.locator("div[role='grid'], span[title='Andriza'], div[contenteditable='true']").count() > 0:
                print(f"✅ WhatsApp Web loaded successfully after {(i+1)*3}s!")
                break
            else:
                print(f"Syncing... ({(i+1)*3}s)")

        page.screenshot(path="scratch/wa_logged_in_verified.png")
        title = page.title()
        is_ready = page.locator("div[role='grid'], span[title='Andriza'], div[contenteditable='true']").count() > 0
        print(f"Page Title: {title}")
        print(f"Session Status: {'✅ LOGGED IN & READY' if is_ready else 'SYNCING IN PROGRESS'}")
        browser.close()

if __name__ == "__main__":
    main()
