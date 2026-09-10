from playwright.sync_api import sync_playwright
import time

def main():
    print("Connecting to CDP to read messages from the CURRENT active chat...")
    with sync_playwright() as p:
        try:
            browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
            context = browser.contexts[0]
            page = context.pages[0]
            
            rows = page.locator('div[role="row"]').all()
            if not rows:
                print("No messages found on screen. Reloading page...")
                page.reload()
                time.sleep(10)
            
            print("Scrolling up to load older messages...")
            for _ in range(15):
                rows = page.locator('div[role="row"]').all()
                if rows:
                    try:
                        rows[0].scroll_into_view_if_needed()
                        time.sleep(1.5)
                    except:
                        pass
            
            print("Extracting recent messages...")
            message_rows = page.locator('div[role="row"]').all()
            
            print("\n--- LATEST MESSAGES ---")
            for i, row in enumerate(message_rows[-80:]):
                try:
                    text = row.inner_text().replace('\n', ' | ')
                    print(f"[{i+1}] {text}")
                except:
                    pass
            
            print("\nDone reading messages.")
            browser.disconnect()
            
        except Exception as e:
            print(f"Failed to read messages: {e}")

if __name__ == "__main__":
    main()
