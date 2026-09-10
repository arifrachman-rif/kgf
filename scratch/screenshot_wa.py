from playwright.sync_api import sync_playwright

def main():
    with sync_playwright() as p:
        try:
            print("Connecting to browser...")
            browser = p.chromium.connect_over_cdp("http://localhost:9222")
            page = browser.contexts[0].pages[0]
            
            print(f"Current URL: {page.url}")
            page.screenshot(path="/mnt/c/Users/rifra/.gemini/antigravity-ide/brain/bbb42104-e7a1-4e39-ae60-4b482e7dcca9/whatsapp_status_2.png")
            print("Screenshot saved.")
            
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    main()
