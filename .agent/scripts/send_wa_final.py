from playwright.sync_api import sync_playwright
import os

def main():
    contact_name = "Faizal Riza"
    message = "Berikut adalah hasil analisa profil perusahaan Pevesindo (PT Alastri Teguh International) yang diminta: https://docs.google.com/document/d/1noxGFJmYnh1BmWu6-DbI2ka1IdDXgTfGDwZrF86u7xA/edit?usp=drivesdk"
    user_data_dir = os.path.expanduser("~/.config/antigravity-chrome-data")
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                headless=False,
                args=["--disable-gpu", "--no-sandbox", "--disable-dev-shm-usage"]
            )
            page = browser.pages[0] if browser.pages else browser.new_page()
            page.goto("https://web.whatsapp.com")
            
            print("Mencari kotak teks menggunakan pelacak Shadow DOM...")
            
            # get_by_role("textbox") otomatis menembus Shadow DOM milik Lexical Meta
            textboxes = page.get_by_role("textbox")
            textboxes.first.wait_for(state="visible", timeout=60000)
            
            print("Kotak pencarian ditemukan! Mengetik...")
            textboxes.first.fill(contact_name)
            
            # Beri waktu pencarian untuk muncul
            page.wait_for_timeout(3000)
            
            # Cari nama kontak (bisa di title atau text)
            contact = page.get_by_title(contact_name).first
            
            contact.wait_for(state="visible", timeout=15000)
            contact.click()
            
            print("Chat terbuka. Mengetik pesan...")
            page.wait_for_timeout(2000)
            
            message_box = textboxes.last
            message_box.fill(message)
            message_box.press("Enter")
            
            print("PESAN BERHASIL DIKIRIM!")
            page.wait_for_timeout(3000)
            browser.close()
    except Exception as e:
        print(f"Gagal: {e}")

if __name__ == "__main__":
    main()
