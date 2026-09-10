from playwright.sync_api import sync_playwright

def main():
    with sync_playwright() as p:
        try:
            print("Connecting to browser...")
            browser = p.chromium.connect_over_cdp("http://localhost:9222")
            page = browser.contexts[0].pages[0]
            
            # Clear search if X button exists
            cancel_btn = page.locator('button[aria-label="Cancel search"]')
            if cancel_btn.count() > 0:
                cancel_btn.click()
                page.wait_for_timeout(1000)
            
            print("Typing in search box...")
            search_box = page.get_by_role("textbox").first
            search_box.click()
            search_box.fill("Brian Arfi")
            page.wait_for_timeout(2000)
            
            print("Clicking Brian Arfi chat...")
            page.locator('span[title="Brian Arfi"]').first.click()
            page.wait_for_timeout(4000)
            
            print("Scrolling up to load older messages...")
            # Hover over a copyable text to focus the pane
            first_msg = page.locator('div.copyable-text').first
            first_msg.hover()
            
            for _ in range(40):
                page.mouse.wheel(0, -10000)
                page.wait_for_timeout(400)
            
            print("Extracting messages...")
            messages = page.locator('div.copyable-text').all_inner_texts()
            
            found = False
            for m in messages:
                if "http" in m or "ai" in m.lower() or "circle" in m.lower() or "affiliate" in m.lower():
                    print("-" * 40)
                    print(m)
                    found = True
                    
            if not found:
                print("No affiliate link or AI circle mentions found in the recent messages!")
            
            print("Done")
            
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    main()
