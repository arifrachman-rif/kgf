from playwright.sync_api import sync_playwright
import sys
import time

def check_connection():
    try:
        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
            context = browser.contexts[0]
            
            # Cari tab WhatsApp
            page = None
            for pg in context.pages:
                if "whatsapp" in pg.url.lower():
                    page = pg
                    break
            
            if not page:
                page = context.new_page()
                page.goto("https://web.whatsapp.com")
            
            # Beri waktu render
            page.wait_for_timeout(5000)
            
            content = page.content().lower()
            if "use whatsapp on your computer" in content or "link with phone number" in content or "tautkan dengan nomor telepon" in content or "gunakan whatsapp di komputer" in content:
                print("DISCONNECTED")
                sys.exit(1)
            else:
                print("CONNECTED")
                sys.exit(0)
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(2)

if __name__ == "__main__":
    check_connection()
