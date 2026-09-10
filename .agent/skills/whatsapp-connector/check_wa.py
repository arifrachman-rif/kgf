import sys
from playwright.sync_api import sync_playwright

WA_URL = "https://web.whatsapp.com"

def check_wa():
    p = sync_playwright().start()
    try:
        browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        context = browser.contexts[0]
        
        page = None
        for pg in context.pages:
            if "whatsapp" in pg.url.lower():
                page = pg
                break
                
        if not page:
            page = context.pages[0] if context.pages else context.new_page()
            page.goto(WA_URL)
            
        print("Connected to CDP. Checking WA status...")
        if "whatsapp" not in page.url.lower():
            page.goto(WA_URL)
            page.wait_for_load_state("networkidle", timeout=15000)
            
        # "Any textbox is visible" is NOT a login test: the QR screen's phone
        # number field is a textbox too, so that check reports a logged-out
        # session as ready. The chat list pane only exists once logged in.
        try:
            page.locator("#pane-side").wait_for(state="visible", timeout=10000)
            print("WhatsApp is connected and ready.")
        except Exception:
            print("WhatsApp is NOT logged in (chat list absent).")
            if page.locator("canvas").count():
                print("QR Code detected. Authentication required.")
            elif page.get_by_text("Enter phone number").count():
                print("Phone-number login screen is open.")
            else:
                print("Could not confirm connection. Please verify manually.")
    except Exception as e:
        print(f"Error checking WA: {e}")
    finally:
        try:
            browser.close()
        except:
            pass
        p.stop()

if __name__ == "__main__":
    check_wa()
