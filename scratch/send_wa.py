from playwright.sync_api import sync_playwright
import time

def send_message(page, contact_name, message):
    print(f"Searching for {contact_name}...")
    
    # Clear search if X button exists
    cancel_btn = page.locator('button[aria-label="Cancel search"]')
    if cancel_btn.count() > 0:
        cancel_btn.click()
        page.wait_for_timeout(1000)
        
    search_box = page.get_by_role("textbox").first
    search_box.click()
    search_box.fill(contact_name)
    page.wait_for_timeout(3000)
    
    print(f"Clicking {contact_name} chat...")
    # Find the title that contains the contact name
    contact_loc = page.locator(f'span[title*="{contact_name}"]')
    if contact_loc.count() > 0:
        contact_loc.first.click()
    else:
        print(f"Could not find exact title, trying text search for {contact_name}...")
        page.locator(f'span:has-text("{contact_name}")').first.click()
        
    page.wait_for_timeout(3000)
    
    print("Typing message...")
    textboxes = page.get_by_role("textbox").all()
    if len(textboxes) > 1:
        textboxes[1].click()
    else:
        page.locator('div[contenteditable="true"][data-tab="10"]').click()
        
    page.keyboard.type(message, delay=10)
    page.wait_for_timeout(500)
    page.keyboard.press("Enter")
    page.wait_for_timeout(2000)
    print(f"Message sent to {contact_name}.")

def main():
    with sync_playwright() as p:
        try:
            print("Connecting to browser...")
            browser = p.chromium.connect_over_cdp("http://localhost:9222")
            page = browser.contexts[0].pages[0]
            
            # Ensure we are on WhatsApp Web
            if "web.whatsapp.com" not in page.url:
                page.goto("https://web.whatsapp.com")
                page.wait_for_load_state("networkidle")
                page.wait_for_timeout(15000) # Wait for QR or load
            
            msg = "Draf Pitch Deck untuk Elea Foundation sudah siap. Silakan cek di sini: https://docs.google.com/document/d/1EnAEf8VZfvryuDxuyBWgyaQgef-tCW86jmNB2hqTdlY/edit"
            
            send_message(page, "Yuyun Kurniawan", msg)
            send_message(page, "Arif Rachman", msg)
            
            print("All done.")
            
        except Exception as e:
            print(f"Error: {e}")
            page.screenshot(path="/mnt/c/Users/rifra/.gemini/antigravity-ide/brain/bbb42104-e7a1-4e39-ae60-4b482e7dcca9/whatsapp_error.png")

if __name__ == "__main__":
    main()
