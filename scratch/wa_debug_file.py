import sys
import argparse
from playwright.sync_api import sync_playwright

def test_file_upload(to, file_path):
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp("http://localhost:9222")
        context = browser.contexts[0]
        page = context.pages[0]
        
        # Cari chat
        textboxes = page.get_by_role("textbox")
        textboxes.first.wait_for(state="visible", timeout=60000)
        textboxes.first.fill(to)
        page.wait_for_timeout(2000)
        
        contact = page.locator(f'span[title="{to}"]').first
        if not contact.is_visible():
            contact = page.get_by_text(to).first
            
        contact.wait_for(state="visible", timeout=15000)
        contact.click()
        page.wait_for_timeout(2000)
        
        print(f"Melampirkan file: {file_path}", file=sys.stderr)
        # Ambil screenshot sebelum upload
        page.screenshot(path="scratch/wa_before_upload.png")
        
        try:
            # Mencoba upload
            page.locator('input[type="file"]').last.set_input_files(file_path)
            page.wait_for_timeout(3000)
            
            # Ambil screenshot saat preview seharusnya muncul
            page.screenshot(path="scratch/wa_preview_upload.png")
            
            # Coba tekan tombol kirim file (tombol dengan aria-label "Send" di halaman pratinjau)
            send_btn = page.locator('div[aria-label="Send"]')
            if send_btn.is_visible():
                print("Ditemukan tombol Send! Mengkliknya...")
                send_btn.click()
            else:
                print("Tombol Send tidak terlihat, menekan Enter...")
                page.keyboard.press("Enter")
                
            page.wait_for_timeout(3000)
            # Ambil screenshot setelah klik send
            page.screenshot(path="scratch/wa_after_upload.png")
        except Exception as e:
            print(f"Gagal saat upload: {e}")
            
if __name__ == "__main__":
    test_file_upload("Nyokap", "scratch/SHM_Enggal_1.pdf")
