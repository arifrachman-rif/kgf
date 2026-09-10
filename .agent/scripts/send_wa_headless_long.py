from playwright.sync_api import sync_playwright
import os

def main():
    contact_name = "Faizal Riza"
    message = "Berikut adalah hasil analisa profil perusahaan Pevesindo (PT Alastri Teguh International) yang diminta: https://docs.google.com/document/d/1noxGFJmYnh1BmWu6-DbI2ka1IdDXgTfGDwZrF86u7xA/edit?usp=drivesdk"
    user_data_dir = os.path.expanduser("~/.config/antigravity-chrome-data")
    
    try:
        with sync_playwright() as p:
            print("Membuka WhatsApp secara diam-diam (headless) seperti semula...")
            browser = p.chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                headless=True,
                args=["--disable-gpu", "--no-sandbox", "--disable-dev-shm-usage"]
            )
            page = browser.pages[0] if browser.pages else browser.new_page()
            page.goto("https://web.whatsapp.com")
            
            print("Menunggu loading obrolan (maksimal 3 menit karena loading WA Web cukup lama)...")
            
            textboxes = page.get_by_role("textbox")
            # Set timeout menjadi 180 detik
            textboxes.first.wait_for(state="visible", timeout=180000)
            
            print("Berhasil dimuat! Mencari Faizal Riza...")
            textboxes.first.fill(contact_name)
            page.wait_for_timeout(3000)
            
            contact = page.get_by_title(contact_name).first
            contact.wait_for(state="visible", timeout=15000)
            contact.click()
            
            print("Mengetik dan mengirim pesan...")
            page.wait_for_timeout(2000)
            
            message_box = textboxes.last
            message_box.fill(message)
            message_box.press("Enter")
            
            print("PESAN BERHASIL DIKIRIM!")
            page.wait_for_timeout(5000)
            browser.close()
    except Exception as e:
        print(f"Gagal: {e}")

if __name__ == "__main__":
    main()
