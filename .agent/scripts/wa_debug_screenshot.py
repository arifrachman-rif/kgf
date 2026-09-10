from playwright.sync_api import sync_playwright
import os

USER_DATA_DIR = os.path.expanduser("~/.config/antigravity-chrome-data")

def main():
    print("Mengambil screenshot dari dalam Xvfb...")
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch_persistent_context(
                user_data_dir=USER_DATA_DIR,
                headless=False,
                args=["--disable-gpu", "--no-sandbox", "--disable-dev-shm-usage"]
            )
            page = browser.pages[0] if browser.pages else browser.new_page()
            page.goto("https://web.whatsapp.com")
            
            print("Menunggu 25 detik agar halaman termuat...")
            page.wait_for_timeout(25000)
            
            path = "/mnt/c/Users/rifra/.gemini/antigravity-ide/brain/bbb42104-e7a1-4e39-ae60-4b482e7dcca9/wa_debug_xvfb.png"
            page.screenshot(path=path, full_page=True)
            print(f"Screenshot tersimpan di {path}")
            
            browser.close()
    except Exception as e:
        print(f"Gagal: {e}")

if __name__ == "__main__":
    main()
