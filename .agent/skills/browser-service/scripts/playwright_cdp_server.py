from playwright.sync_api import sync_playwright
import time
import os
import signal
import sys

def handle_sigterm(*args):
    sys.exit(0)

signal.signal(signal.SIGTERM, handle_sigterm)
signal.signal(signal.SIGINT, handle_sigterm)

def main():
    print("Starting robust Playwright CDP server (Xvfb Ghost Mode)...")
    with sync_playwright() as p:
        user_data_dir = os.path.expanduser("~/.config/antigravity-chrome-data")
        browser = p.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=False, # HARUS False agar lolos anti-bot WA, tetapi disembunyikan oleh Xvfb
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            args=[
                "--disable-gpu", 
                "--no-sandbox", 
                "--disable-dev-shm-usage",
                "--remote-debugging-port=9222",
                "--remote-debugging-address=127.0.0.1"
            ]
        )
        print("✅ Playwright CDP server running stably on port 9222.")
        
        # Buka tab khusus untuk WhatsApp agar selalu tersinkronisasi di latar belakang
        page = browser.pages[0] if browser.pages else browser.new_page()
        page.goto("https://web.whatsapp.com")
        print("✅ WhatsApp Web opened in background for permanent sync.")
        
        # Keep the process alive indefinitely so the session remains active
        try:
            while True:
                time.sleep(3600)
        except (KeyboardInterrupt, SystemExit):
            print("Shutting down CDP server.")

if __name__ == "__main__":
    main()
