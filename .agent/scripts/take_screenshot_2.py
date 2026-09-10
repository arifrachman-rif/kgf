from playwright.sync_api import sync_playwright
import time

def main():
    try:
        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
            context = browser.contexts[0]
            page = context.pages[0] if context.pages else context.new_page()
            
            print("Navigating to WhatsApp Web...")
            page.goto("https://web.whatsapp.com", wait_until="load")
            
            # Tunggu elemen Canvas (QR Code) atau Search Bar muncul
            try:
                page.wait_for_selector('canvas, div[contenteditable="true"][data-tab="3"]', timeout=45000)
                time.sleep(5) # Jeda ekstra agar QR Code termuat utuh
            except:
                print("Timeout waiting for QR code.")
                
            path = "/mnt/c/Users/rifra/.gemini/antigravity-ide/brain/bbb42104-e7a1-4e39-ae60-4b482e7dcca9/whatsapp_qr_fix.png"
            page.screenshot(path=path)
            browser.disconnect()
            print("Screenshot saved.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
