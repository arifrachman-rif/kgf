from playwright.sync_api import sync_playwright
import time
import os

def main():
    contact_name = "Faizal Riza"
    message = "Berikut adalah hasil analisa profil perusahaan Pevesindo (PT Alastri Teguh International) yang diminta: https://docs.google.com/document/d/1noxGFJmYnh1BmWu6-DbI2ka1IdDXgTfGDwZrF86u7xA/edit?usp=drivesdk"
    
    user_data_dir = os.path.expanduser("~/.config/antigravity-chrome-data")
    
    try:
        with sync_playwright() as p:
            print("Launching VISIBLE browser for WhatsApp...")
            # Menggunakan headless=False agar jendela browser muncul di layar Anda
            browser = p.chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                headless=False,
                args=["--disable-gpu", "--no-sandbox", "--disable-dev-shm-usage"]
            )
            
            page = browser.pages[0] if browser.pages else browser.new_page()
            
            print("Navigating to WhatsApp Web...")
            page.goto("https://web.whatsapp.com")
            
            print("\n=======================================================")
            print("MOHON PERHATIAN: Jendela browser Chrome (Playwright) seharusnya muncul di layar Anda.")
            print("Jika layar meminta QR Code, SILAKAN SCAN SEKARANG.")
            print("Skrip ini akan menunggu hingga 5 menit sebelum time-out...")
            print("=======================================================\n")
            
            # Tunggu kotak pencarian (indikator bahwa Anda sudah masuk) hingga 5 menit
            search_bar = page.locator('div[contenteditable="true"][data-tab="3"]')
            search_bar.wait_for(state="visible", timeout=300000)
            
            print(f"Login terkonfirmasi! Mencari kontak: {contact_name}")
            search_bar.fill(contact_name)
            
            # Cari dan klik kontak
            contact_element = page.locator(f'span[title="{contact_name}"]')
            contact_element.wait_for(state="visible", timeout=15000)
            contact_element.first.click()
            
            # Ketik dan kirim pesan
            message_box = page.locator('div[contenteditable="true"][data-tab="10"]')
            message_box.wait_for(state="visible", timeout=10000)
            
            print("Mengetik dan mengirim pesan...")
            message_box.fill(message)
            message_box.press("Enter")
            
            print("PESAN BERHASIL DIKIRIM!")
            page.wait_for_timeout(3000)
            browser.close()
            
    except Exception as e:
        print(f"Gagal mengirim pesan: {e}")

if __name__ == "__main__":
    main()
