from playwright.sync_api import sync_playwright
import os

def main():
    user_data_dir = os.path.expanduser("~/.config/antigravity-chrome-data")
    try:
        with sync_playwright() as p:
            print("Launching headless browser to dump WhatsApp DOM...")
            browser = p.chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                headless=True,
                args=["--disable-gpu", "--no-sandbox", "--disable-dev-shm-usage"]
            )
            page = browser.pages[0] if browser.pages else browser.new_page()
            page.goto("https://web.whatsapp.com", wait_until="networkidle")
            
            print("Waiting 15 seconds for chats to load...")
            page.wait_for_timeout(15000)
            
            html = page.content()
            out_path = "/mnt/c/Users/rifra/.gemini/antigravity-ide/brain/bbb42104-e7a1-4e39-ae60-4b482e7dcca9/wa_dom.html"
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(html)
            
            browser.close()
            print(f"DOM dumped to {out_path}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
