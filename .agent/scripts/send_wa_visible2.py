from playwright.sync_api import sync_playwright
import os

def main():
    contact_name = "Faizal Riza"
    message = "Berikut adalah hasil analisa profil perusahaan Pevesindo (PT Alastri Teguh International) yang diminta: https://docs.google.com/document/d/1noxGFJmYnh1BmWu6-DbI2ka1IdDXgTfGDwZrF86u7xA/edit?usp=drivesdk"
    
    user_data_dir = os.path.expanduser("~/.config/antigravity-chrome-data")
    
    try:
        with sync_playwright() as p:
            print("Launching VISIBLE browser for WhatsApp...")
            browser = p.chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                headless=False,
                args=["--disable-gpu", "--no-sandbox", "--disable-dev-shm-usage"]
            )
            
            page = browser.pages[0] if browser.pages else browser.new_page()
            page.goto("https://web.whatsapp.com")
            
            print("Menunggu antarmuka WhatsApp Web termuat sepenuhnya...")
            
            # Kita gunakan selektor yang lebih kebal terhadap update UI WhatsApp (hanya mencari kotak teks apa pun)
            textboxes = page.locator('div[contenteditable="true"]')
            
            # Menunggu kotak teks pertama (Search Bar) muncul (timeout 60 detik)
            textboxes.first.wait_for(state="visible", timeout=60000)
            
            print(f"Mengetik nama kontak: {contact_name}")
            search_bar = textboxes.first
            search_bar.fill(contact_name)
            
            # Cari nama kontaknya
            contact_element = page.locator(f'span[title="{contact_name}"]')
            contact_element.wait_for(state="visible", timeout=15000)
            contact_element.first.click()
            
            print("Kontak ditemukan! Mengetik pesan...")
            # Setelah chat diklik, kotak teks pesan (Message Box) biasanya menjadi kotak teks yang terakhir
            message_box = textboxes.last
            message_box.wait_for(state="visible", timeout=10000)
            message_box.fill(message)
            message_box.press("Enter")
            
            print("PESAN BERHASIL DIKIRIM!")
            page.wait_for_timeout(3000)
            browser.close()
            
    except Exception as e:
        print(f"Gagal mengirim pesan: {e}")

if __name__ == "__main__":
    main()
