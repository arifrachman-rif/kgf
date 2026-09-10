from playwright.sync_api import sync_playwright

def main():
    try:
        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
            context = browser.contexts[0]
            page = context.pages[0]
            page.set_viewport_size({"width": 1920, "height": 1080})
            page.screenshot(path="wa_status.png")
            browser.disconnect()
            print("Screenshot taken.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
