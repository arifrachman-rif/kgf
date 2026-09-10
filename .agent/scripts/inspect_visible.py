from playwright.sync_api import sync_playwright
import os

def main():
    user_data_dir = os.path.expanduser("~/.config/antigravity-chrome-data")
    try:
        with sync_playwright() as p:
            print("Launching VISIBLE browser for DOM Inspection...")
            browser = p.chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                headless=False,
                args=["--disable-gpu", "--no-sandbox", "--disable-dev-shm-usage"]
            )
            page = browser.pages[0] if browser.pages else browser.new_page()
            page.goto("https://web.whatsapp.com")
            
            print("Menunggu 20 detik agar obrolan termuat...")
            page.wait_for_timeout(20000)
            
            out_path = "/mnt/c/Users/rifra/.gemini/antigravity-ide/brain/bbb42104-e7a1-4e39-ae60-4b482e7dcca9/wa_dom_visible.html"
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(page.content())
            
            browser.close()
            print("Berhasil mengambil struktur HTML terbaru!")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
