from playwright.sync_api import sync_playwright
import sys

def main():
    contact_name = "Faizal Riza"
    message = "Berikut adalah hasil analisa profil perusahaan Pevesindo (PT Alastri Teguh International) yang diminta: https://docs.google.com/document/d/1noxGFJmYnh1BmWu6-DbI2ka1IdDXgTfGDwZrF86u7xA/edit?usp=drivesdk"

    try:
        with sync_playwright() as p:
            print("Connecting to local CDP server...")
            # Menghubungkan ke sesi Chrome persisten yang sudah berjalan di WSL
            browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
            
            context = browser.contexts[0]
            page = context.pages[0] if context.pages else context.new_page()
            
            print("Navigating to WhatsApp Web...")
            page.goto("https://web.whatsapp.com")
            
            # Tunggu kotak pencarian (tanda bahwa kita sudah login)
            search_bar = page.locator('div[contenteditable="true"][data-tab="3"]')
            search_bar.wait_for(state="visible", timeout=60000)
            
            print(f"Searching for contact: {contact_name}")
            search_bar.fill(contact_name)
            
            # Tunggu hasil pencarian muncul dan klik namanya
            contact_element = page.locator(f'span[title="{contact_name}"]')
            contact_element.wait_for(state="visible", timeout=15000)
            contact_element.first.click()
            
            # Tunggu kotak teks pesan terbuka
            message_box = page.locator('div[contenteditable="true"][data-tab="10"]')
            message_box.wait_for(state="visible", timeout=10000)
            
            print("Typing and sending message...")
            message_box.fill(message)
            message_box.press("Enter")
            
            print("Message sent successfully via Python Playwright fallback!")
            
            # Tunggu sebentar agar pesan benar-benar terkirim sebelum putus koneksi
            page.wait_for_timeout(3000)
            browser.disconnect()
            
    except Exception as e:
        print(f"Failed to send WhatsApp message: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
