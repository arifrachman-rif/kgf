from playwright.sync_api import sync_playwright
import os
import sys

def main():
    print("Membuka Chrome secara kasatmata untuk scan QR Code...")
    with sync_playwright() as p:
        user_data_dir = os.path.expanduser("~/.config/antigravity-chrome-data")
        browser = p.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=False,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            args=[
                "--disable-gpu", 
                "--no-sandbox", 
                "--disable-dev-shm-usage"
            ]
        )
        page = browser.pages[0] if browser.pages else browser.new_page()
        page.goto("https://web.whatsapp.com")
        
        print("Silakan scan QR code di jendela Chrome yang muncul.")
        print("Menunggu sampai daftar chat muncul (tanda berhasil login)...")
        
        try:
            # Tunggu elemen textbox pencarian kontak (muncul setelah login berhasil)
            # Timeout dinaikkan ke 120 detik (2 menit) untuk memberi waktu scan
            page.get_by_role("textbox").first.wait_for(state="visible", timeout=120000)
            print("Berhasil login! Menyimpan sesi dan menutup browser...")
        except Exception as e:
            print(f"Gagal login atau timeout (2 menit): {e}")
            sys.exit(1)
        
        # Jeda 3 detik agar cookie tersimpan dengan baik
        page.wait_for_timeout(3000)
        browser.close()

if __name__ == "__main__":
    main()
