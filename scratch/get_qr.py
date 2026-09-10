from playwright.sync_api import sync_playwright
import time

def main():
    print("Connecting to stable background Chromium...")
    with sync_playwright() as p:
        try:
            browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
            context = browser.contexts[0] if browser.contexts else browser.new_context()
            page = context.pages[0] if context.pages else context.new_page()
            
            print("Navigating to WhatsApp Web...")
            page.goto("https://web.whatsapp.com", timeout=60000)
            print("Waiting for page to load (looking for QR code)...")
            
            try:
                # The canvas holds the QR code
                page.wait_for_selector("canvas", timeout=30000)
                time.sleep(3) # Let it render fully
                print("QR code canvas found! Taking screenshot...")
                page.screenshot(path="whatsapp_qr.png")
                print("Screenshot saved to whatsapp_qr.png")
            except Exception as e:
                print(f"Could not find QR code canvas within 30s. Reason: {e}")
                print("Taking a screenshot of the current state anyway...")
                page.screenshot(path="whatsapp_qr.png")
            
            # CRITICAL: We DISCONNECT instead of close so the browser stays alive!
            browser.disconnect()
            print("Disconnected from browser. Browser is still running!")
        except Exception as e:
            print(f"Failed: {e}")

if __name__ == "__main__":
    main()
