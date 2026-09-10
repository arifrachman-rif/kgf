from playwright.sync_api import sync_playwright
import sys
import time

def main():
    try:
        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
            context = browser.contexts[0]
            page = context.pages[0]
            
            print("Mencari chat Yuli BSI di layar atau textbox...")
            
            yuli = page.get_by_text("Yuli BSI", exact=False).first
            
            if not yuli.is_visible():
                textboxes = page.get_by_role("textbox")
                textboxes.first.wait_for(state="visible", timeout=60000)
                textboxes.first.fill("Yuli BSI")
                page.wait_for_timeout(2000)
                contact = page.get_by_title("Yuli BSI").first
                if not contact.is_visible():
                    contact = page.get_by_text("Yuli BSI").first
                contact.wait_for(state="visible", timeout=15000)
                contact.click()
            else:
                yuli.click()
            
            page.wait_for_timeout(2000)
            
            print("Chat ditemukan. Melampirkan 8 file KTP sekaligus...")
            files = [
                "/mnt/c/Users/rifra/Downloads/KTP Enum Mutiara/Mahendra Sadepi.png",
                "/mnt/c/Users/rifra/Downloads/KTP Enum Mutiara/Nanda Tryas Wicaksana.png",
                "/mnt/c/Users/rifra/Downloads/KTP Enum Mutiara/Pitra.png",
                "/mnt/c/Users/rifra/Downloads/KTP Enum Mutiara/Yuda Adi Pradana.png",
                "/mnt/c/Users/rifra/Downloads/KTP Enum Mutiara/Arif Rahman.png",
                "/mnt/c/Users/rifra/Downloads/KTP Enum Mutiara/Asep Hilmansyah.png",
                "/mnt/c/Users/rifra/Downloads/KTP Enum Mutiara/Fadillah Nurachman.png",
                "/mnt/c/Users/rifra/Downloads/KTP Enum Mutiara/Fairuz Al Fajri.png"
            ]
            
            # Klik tombol Attachment
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
            print("File dimuat ke antarmuka, menunggu konfirmasi upload...")
            page.wait_for_timeout(4000)
            
            print("Mengklik tombol kirim...")
            send_btn = page.locator('div[aria-label="Send"]').first
            if send_btn.is_visible():
                send_btn.click()
            else:
                page.keyboard.press("Enter")
                
            print("8 FILE KTP BERHASIL DIKIRIM!")
            page.wait_for_timeout(5000)
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
