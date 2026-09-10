from playwright.sync_api import sync_playwright
import sys
import time

def main():
    try:
        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
            context = browser.contexts[0]
            page = context.pages[0]
            
            print("Menunggu proses loading sinkronisasi WhatsApp (Don't close this window)...")
            
            for i in range(60): # 60 * 5 = 300 detik (5 menit maksimal)
                all_text = page.locator('body').inner_text()
                if "Loading your chats" in all_text or "messages are downloading" in all_text:
                    if i % 2 == 0:
                        print(f"Masih loading sinkronisasi... ({i*5} detik berlalu)")
                    time.sleep(5)
                else:
                    print("Loading selesai! Antarmuka siap digunakan.")
                    break
            
            print("Mencari chat Yuli BSI di layar...")
            page.wait_for_timeout(2000) # Jeda ekstra setelah loading
            yuli = page.get_by_text("Yuli BSI", exact=False).first
            
            if yuli.is_visible():
                yuli.click()
                print("Berhasil mengklik obrolan Yuli BSI!")
                page.wait_for_timeout(3000)
                
                print("=== NAMA FILE KK YANG TERDETEKSI ===")
                spans = page.locator('span[title]').all()
                for span in spans:
                    title = span.get_attribute("title")
                    if title and ("KK" in title or ".pdf" in title.lower() or ".jpg" in title.lower() or ".png" in title.lower()):
                        print(title)
            else:
                print("Yuli BSI tidak terlihat langsung. Mencoba via pencarian (textbox)...")
                search_box = None
                textboxes = page.locator('div[contenteditable="true"]').all()
                for box in textboxes:
                    if box.is_visible():
                        search_box = box
                        break
                
                if search_box:
                    search_box.click()
                    search_box.fill("Yuli BSI")
                    page.wait_for_timeout(2000)
                    page.keyboard.press("Enter")
                    page.wait_for_timeout(3000)
                    
                    print("=== NAMA FILE KK YANG TERDETEKSI ===")
                    spans = page.locator('span[title]').all()
                    for span in spans:
                        title = span.get_attribute("title")
                        if title and ("KK" in title or ".pdf" in title.lower() or ".jpg" in title.lower() or ".png" in title.lower()):
                            print(title)
                else:
                    print("Gagal menemukan kotak pencarian setelah loading.")
                    sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
