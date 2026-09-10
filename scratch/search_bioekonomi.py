from playwright.sync_api import sync_playwright
import time

group_name = "BioEkonomi"

def main():
    print(f"Connecting to CDP to find and read '{group_name}'...")
    with sync_playwright() as p:
        try:
            browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
            context = browser.contexts[0]
            page = context.pages[0]
            page.set_viewport_size({"width": 1920, "height": 1080})
            
            # Anti-bot spoofing
            try:
                page.evaluate("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            except:
                pass
            
            # If search box is hidden behind an icon (narrow viewport mode)
            try:
                icon = page.locator('span[data-icon="search"]')
                if icon.is_visible():
                    icon.click()
                    time.sleep(1)
            except:
                pass
                
            print("Waiting for search box...")
            search_box = page.locator('input[placeholder="Search or start a new chat"]').or_(page.locator('div[title="Search input textbox"]'))
            
            try:
                search_box.wait_for(timeout=15000)
            except Exception as e:
                print("Still loading... triggering a page refresh to break the loop!")
                page.reload()
                search_box.wait_for(timeout=40000)
            
            print(f"Searching for '{group_name}'...")
            search_box.click()
            time.sleep(1)
            page.keyboard.type(group_name, delay=100)
            time.sleep(3) # wait for results to filter
            
            page.keyboard.press("Enter")
            time.sleep(4) # wait for chat pane to open
            
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
            
            print(f"\n--- LATEST MESSAGES IN {group_name} ---")
            for i, row in enumerate(message_rows[-80:]):
                try:
                    text = row.inner_text().replace('\n', ' | ')
                    print(f"[{i+1}] {text}")
                except:
                    pass
            
            print("\nDone reading messages.")
            
        except Exception as e:
            print(f"Failed to read messages: {e}")

if __name__ == "__main__":
    main()
