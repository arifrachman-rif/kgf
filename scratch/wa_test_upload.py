import sys
from playwright.sync_api import sync_playwright

def main():
    to = "Nyokap"
    file_path = "scratch/SHM_Enggal_1.pdf"
    
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp("http://localhost:9222")
        context = browser.contexts[0]
        page = context.pages[0]
        
        # Cari chat
        print("Mencari chat...")
        textboxes = page.get_by_role("textbox")
        textboxes.first.wait_for(state="visible", timeout=60000)
        textboxes.first.fill(to)
        page.wait_for_timeout(2000)
        
        contact = page.get_by_title(to).first
        if not contact.is_visible():
            contact = page.get_by_text(to).first
            
        contact.wait_for(state="visible", timeout=15000)
        contact.click()
        page.wait_for_timeout(2000)
        
        # Kirim file menggunakan UI click
        print("Klik tombol Attach...")
        page.locator('button[aria-label="Attach"]').click()
        page.wait_for_timeout(1000)
        
        print("Mencari tombol Document...")
        # Tombol Document sering berupa menuitem atau li
        # The easiest way is looking for a span or anything with text "Document" or data-icon="document"
        doc_btn = page.locator('ul li:has-text("Document")').first
        if not doc_btn.is_visible():
            doc_btn = page.locator('span:text("Document")').first
            
        if not doc_btn.is_visible():
            print("Fallback ke Document dari list menu item...")
            # Dump all li texts
            lis = page.locator('li').all()
            for li in lis:
                print("LI:", li.inner_text())
                
            doc_btn = page.locator('li:has(span[data-icon="document"])').first
            
        print("Membuka file chooser...")
        with page.expect_file_chooser() as fc_info:
            doc_btn.click()
            
        file_chooser = fc_info.value
        print(f"Mengisi file: {file_path}")
        file_chooser.set_files(file_path)
        
        page.wait_for_timeout(3000)
        
        # Cari dan klik tombol kirim
        print("Mengklik tombol kirim (aria-label='Send')...")
        send_btn = page.locator('div[aria-label="Send"]')
        if send_btn.is_visible():
            send_btn.click()
        else:
            print("Tombol send tidak ditemukan. Menekan Enter...")
            page.keyboard.press("Enter")
            
        print("Selesai menunggu 5 detik...")
        page.wait_for_timeout(5000)

if __name__ == "__main__":
    main()
