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
                print(f"Found 'Andriza' contact!")
                break

        # Force click on Andriza contact
        andriza = page.locator("span[title='Andriza']").first
        andriza.click(force=True)
        page.wait_for_timeout(2000)

        # Download listener
        def on_dl(dl):
            p_out = os.path.join(DEST_DIR, dl.suggested_filename)
            dl.save_as(p_out)
            print(f"✅ DOWNLOADED: {p_out}")

        page.on("download", on_dl)

        # Check for "Click here to get older messages" button
        older_btn = page.get_by_text("Click here to get older messages").first
        if older_btn.is_visible():
            print("Clicking 'get older messages' banner...")
            older_btn.click(force=True)
            page.wait_for_timeout(5000)

        # Scroll down to bottom of chat
        main_chat = page.locator("#main").first
        if not main_chat.is_visible():
            main_chat = page.locator("div[role='region']").first

        for _ in range(5):
            page.keyboard.press("PageDown")
            page.wait_for_timeout(500)

        page.screenshot(path="scratch/wa_andriza_chat_bottom.png")

        # Find images in chat pane
        imgs = main_chat.locator("img[src^='blob:']").all()
        print(f"Found {len(imgs)} blob images in chat pane.")

        dialog = page.locator("div[role='dialog']").first

        for idx, img in enumerate(imgs):
            try:
                print(f"Clicking blob image {idx+1}/{len(imgs)}...")
                img.click(force=True)
                page.wait_for_timeout(2000)

                if dialog.is_visible():
                    print("✅ Lightbox viewer active!")
                    page.screenshot(path=f"scratch/wa_lightbox_active_{idx}.png")
                    
                    # Extract high-res blob image from lightbox
                    lightbox_img = dialog.locator("img[src^='blob:']").first
                    if lightbox_img.is_visible():
                        img_src = lightbox_img.get_attribute("src")
                        if img_src:
                            data_url = page.evaluate("""async (blobUrl) => {
                                try {
                                    const response = await fetch(blobUrl);
                                    const blob = await response.blob();
                                    return new Promise((resolve) => {
                                        const reader = new FileReader();
                                        reader.onloadend = () => resolve(reader.result);
                                        reader.readAsDataURL(blob);
                                    });
                                } catch(e) { return null; }
                            }""", img_src)

                            if data_url and "," in data_url:
                                header_str, encoded = data_url.split(",", 1)
                                ext = "png"
                                if "jpeg" in header_str or "jpg" in header_str:
                                    ext = "jpg"
                                data = base64.b64decode(encoded)
                                out_path = os.path.join(DEST_DIR, f"Logo_KPMI_Image_{idx+1}.{ext}")
                                with open(out_path, "wb") as f:
                                    f.write(data)
                                print(f"✅ Saved logo image file: {out_path}")

                    # Close lightbox
                    page.keyboard.press("Escape")
                    page.wait_for_timeout(1000)

            except Exception as e:
                print(f"Error handling image {idx}: {e}")
                page.keyboard.press("Escape")

        # Check for document attachments
        doc_btns = main_chat.locator("button[aria-label*='Download'], div[title*='Download'], span[data-icon='download']").all()
        for btn in doc_btns:
            try:
                btn.click(force=True)
                page.wait_for_timeout(2000)
            except Exception:
                pass

        page.wait_for_timeout(3000)
        print("\n==========================================")
        print("FINAL SUMMARY OF LOGO KPMI FOLDER:")
        print("==========================================")
        files = os.listdir(DEST_DIR)
        for f in files:
            p_f = os.path.join(DEST_DIR, f)
            print(f" 📄 {f} ({os.path.getsize(p_f)} bytes)")

        browser.close()

if __name__ == "__main__":
    main()
