from playwright.sync_api import sync_playwright
import sys

def main():
    try:
        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
            context = browser.contexts[0]
            page = context.pages[0]
            
            # Cari kontak Diska Amalia
            diska = page.get_by_text("Diska Amalia", exact=False).first
            if not diska.is_visible():
                textboxes = page.get_by_role("textbox")
                textboxes.first.wait_for(state="visible", timeout=60000)
                textboxes.first.fill("Diska Amalia")
                page.wait_for_timeout(2000)
                contact = page.get_by_title("Diska Amalia").first
                if not contact.is_visible():
                    contact = page.get_by_text("Diska Amalia").first
                contact.wait_for(state="visible", timeout=15000)
                contact.click()
            else:
                diska.click()
            
            page.wait_for_timeout(2000)
            
            files = ["/mnt/c/Users/rifra/Downloads/Harga Bu Diska.docx"]
            
            try:
                page.locator('button[aria-label="Attach"]').first.click()
            except:
                page.locator('div[title="Attach"]').first.click()
            
            doc_btn = page.locator('text="Document"').last
            doc_btn.wait_for(state="visible", timeout=10000)
                
            with page.expect_file_chooser() as fc_info:
                doc_btn.click()
                
            file_chooser = fc_info.value
            file_chooser.set_files(files)
            page.wait_for_timeout(4000)
            
            send_btn = page.locator('div[aria-label="Send"]').first
            if send_btn.is_visible():
                send_btn.click()
            else:
                page.keyboard.press("Enter")
                
            print("DOKUMEN BERHASIL DIKIRIM KE DISKA AMALIA!")
            page.wait_for_timeout(5000)
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
