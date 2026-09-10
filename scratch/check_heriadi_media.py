import sys
import os
import time
import base64
from playwright.sync_api import sync_playwright

KTP_DIR = "/mnt/c/Users/rifra/Downloads/KTP Enum Mutiara"
KK_DIR = "/mnt/c/Users/rifra/Downloads/KK Enum Mutiara"

os.makedirs(KTP_DIR, exist_ok=True)
os.makedirs(KK_DIR, exist_ok=True)

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
        
        # Wait for chat UI
        for i in range(25):
            time.sleep(3)
            if page.locator("header, div[role='grid']").count() > 0:
                break

        page.wait_for_timeout(2000)

        # Search Heriadi
        page.keyboard.press("Control+f")
        page.wait_for_timeout(1000)
        page.keyboard.type("Heriadi")
        page.wait_for_timeout(3000)

        heriadi = page.locator("span[title*='Heriadi'], span[title*='heriadi']").first
        if heriadi.is_visible():
            heriadi.click(force=True)
            page.wait_for_timeout(3000)

        # Open Heriadi Contact Info
        header = page.locator("header").last
        header.click(force=True)
        page.wait_for_timeout(3000)
        page.screenshot(path="scratch/wa_heriadi_contact_info.png")

        # Click Media, links and docs
        media_btn = page.get_by_text("Media, links and docs").first
        if not media_btn.is_visible():
            media_btn = page.get_by_text("Media").first

        if media_btn.is_visible():
            media_btn.click(force=True)
            page.wait_for_timeout(3000)
            page.screenshot(path="scratch/wa_heriadi_media_tab.png")

        browser.close()

if __name__ == "__main__":
    main()
