import sys
import os
import time
import base64
from playwright.sync_api import sync_playwright

DEST_DIR = "/mnt/c/Users/rifra/Documents/LOGO KPMI"
os.makedirs(DEST_DIR, exist_ok=True)

def main():
    print(f"Target download directory: {DEST_DIR}")
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
        print("Navigated to WhatsApp Web...")
        
        # Wait for Andriza contact
        for i in range(25):
            time.sleep(2)
            loc = page.locator("span[title='Andriza']").first
            if loc.is_visible():
                print("Found 'Andriza' contact!")
                break

        # Click Andriza contact
        andriza = page.locator("span[title='Andriza']").first
        andriza.click(force=True)
        page.wait_for_timeout(3000)

        main_chat = page.locator("#main").first
        if not main_chat.is_visible():
            main_chat = page.locator("div[role='region']").first

        imgs = main_chat.locator("img[src^='blob:']").all()
        print(f"Found {len(imgs)} blob images in chat pane.")

        for idx, img in enumerate(imgs):
            src = img.get_attribute("src")
            print(f"Extracting blob {idx+1}/{len(imgs)}: {src}")
            try:
                data_url = page.evaluate("""async (blobUrl) => {
                    const response = await fetch(blobUrl);
                    const blob = await response.blob();
                    return new Promise((resolve) => {
                        const reader = new FileReader();
                        reader.onloadend = () => resolve(reader.result);
                        reader.readAsDataURL(blob);
                    });
                }""", src)

                if data_url and "," in data_url:
                    header_str, encoded = data_url.split(",", 1)
                    ext = "png"
                    if "jpeg" in header_str or "jpg" in header_str:
                        ext = "jpg"
                    elif "webp" in header_str:
                        ext = "webp"
                    
                    data = base64.b64decode(encoded)
                    out_name = f"Logo KPMI 3D-{idx+1}.{ext}"
                    if idx == 0:
                        out_name = "Logo KPMI Red 3D.png"
                    
                    out_path = os.path.join(DEST_DIR, out_name)
                    with open(out_path, "wb") as f:
                        f.write(data)
                    print(f"✅ SUCCESSFULLY SAVED: {out_path} ({len(data)} bytes)")
            except Exception as e:
                print(f"Error extracting blob {idx}: {e}")

        print("\n==========================================")
        print("ALL FILES SAVED IN C:\\Users\\rifra\\Documents\\LOGO KPMI:")
        print("==========================================")
        for f in os.listdir(DEST_DIR):
            p_f = os.path.join(DEST_DIR, f)
            print(f" 📄 {f} ({os.path.getsize(p_f)} bytes)")

        browser.close()

if __name__ == "__main__":
    main()
