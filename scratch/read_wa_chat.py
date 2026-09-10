from playwright.sync_api import sync_playwright
import sys
import time

def main():
    print("Membaca obrolan dengan Yuli BSI...")
    try:
        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
            context = browser.contexts[0]
            
            page = None
            for pg in context.pages:
                if "whatsapp" in pg.url.lower():
                    page = pg
                    break
            
            if not page:
                print("Tidak ada tab WhatsApp yang terbuka!")
                sys.exit(1)
            
            print("Menunggu sampai antarmuka WhatsApp termuat (bisa memakan waktu karena sinkronisasi)...")
            
            # Coba cari textbox dengan pengulangan selama 60 detik
            search_box = None
            for i in range(30):
                textboxes = page.locator('div[contenteditable="true"]').all()
                for box in textboxes:
                    if box.is_visible():
                        search_box = box
                        break
                if search_box:
                    break
                time.sleep(2)
                if i % 5 == 0:
                    print(f"Menunggu loading... ({i*2} detik)")
            
            if not search_box:
                print("Gagal menemukan kotak pencarian! Mungkin layar masih loading atau logout.")
                sys.exit(1)
            
            print("Kotak pencarian ditemukan. Membuka obrolan Yuli BSI...")
            search_box.click()
            search_box.fill("Yuli BSI")
            page.wait_for_timeout(2000)
            page.keyboard.press("Enter")
            page.wait_for_timeout(3000)
            
            print("Chat Yuli BSI terbuka, mengekstrak pesan...")
            
            messages = page.locator('div.message-in, div.message-out').all_inner_texts()
            print("=== ISI PESAN ===")
            for msg in messages[-20:]:
                print(msg)
                print("---")
            
            print("=== NAMA FILE YANG TERDETEKSI ===")
            spans = page.locator('span[title]').all()
            for span in spans:
                title = span.get_attribute("title")
                if title and ("KK" in title or ".pdf" in title.lower() or ".jpg" in title.lower() or ".png" in title.lower()):
                    print(title)
            
            sys.exit(0)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
