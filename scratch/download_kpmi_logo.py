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
        andriza = None
        for i in range(20):
            time.sleep(2)
            loc = page.locator("span[title='Andriza']").first
            if loc.is_visible():
                andriza = loc
                print("Found 'Andriza' contact in sidebar!")
                break

        if not andriza:
            print("Contact Andriza not found.")
            browser.close()
            return

        # Click the listitem parent row to open chat
        print("Opening chat by clicking row and pressing Enter...")
        row = page.locator("div[role='listitem']", has=page.locator("span[title='Andriza']")).first
        if row.is_visible():
            row.click()
        else:
            andriza.click()

        page.keyboard.press("Enter")
        page.wait_for_timeout(3000)

        # Confirm chat opened
        page.screenshot(path="scratch/wa_chat_open_confirm.png")
        print("Screenshot saved to scratch/wa_chat_open_confirm.png")

        # Set up download listener
        downloaded_files = []
        def handle_download(download):
            fn = download.suggested_filename
            p_out = os.path.join(DEST_DIR, fn)
            download.save_as(p_out)
            downloaded_files.append(p_out)
            print(f"✅ DOWNLOADED FILE: {p_out}")

        page.on("download", handle_download)

        # Locate the main chat container (#main or div[role='region'])
        main_chat = page.locator("#main").first
        if not main_chat.is_visible():
            main_chat = page.locator("div[role='region']").first

        print("Main chat pane visible:", main_chat.is_visible())

        # Scroll up in main chat pane to load full history
        print("Scrolling chat history...")
        for _ in range(5):
            main_chat.focus()
            page.keyboard.press("PageUp")
            page.wait_for_timeout(1000)

        page.screenshot(path="scratch/wa_main_chat_scrolled.png")

        # Find images in main chat
        imgs = main_chat.locator("img").all()
        print(f"Found {len(imgs)} total images in main chat pane.")

        valid_logo_idx = 1
        for idx, img in enumerate(imgs):
            try:
                src = img.get_attribute("src") or ""
                # Skip profile avatars / icons
                if "avatar" in src or "pp" in src or "emoji" in src:
                    continue

                print(f"Processing chat image {idx+1}/{len(imgs)} (src len={len(src)})...")
                # Click the image to open lightbox viewer
                img.click()
                page.wait_for_timeout(2000)
                page.screenshot(path=f"scratch/wa_lightbox_{idx}.png")

                # In lightbox, check if there's a download button
                # Or extract high-res image src from lightbox dialog
                dialog = page.locator("div[role='dialog']").first
                if dialog.is_visible():
                    print("Lightbox dialog is open.")
                    # Try clicking download button in toolbar
                    dl_btn = dialog.locator("div[title='Download'], button[aria-label='Download'], div[aria-label='Download']").first
                    if dl_btn.is_visible():
                        print("Clicking lightbox download button...")
                        try:
                            with page.expect_download(timeout=5000) as dl_info:
                                dl_btn.click()
                            dl = dl_info.value
                            out = os.path.join(DEST_DIR, dl.suggested_filename)
                            dl.save_as(out)
                            downloaded_files.append(out)
                            print(f"✅ Saved via download button: {out}")
                        except Exception as e:
                            print(f"Download button didn't trigger download event: {e}")

                    # Fallback: fetch blob / image data URL from lightbox image tag
                    lightbox_img = dialog.locator("img").first
                    if lightbox_img.is_visible():
                        img_src = lightbox_img.get_attribute("src")
                        if img_src and (img_src.startswith("blob:") or img_src.startswith("data:")):
                            print("Extracting high-res image blob data from lightbox...")
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
                                out_filename = f"LOGO_KPMI_{valid_logo_idx}.{ext}"
                                out_path = os.path.join(DEST_DIR, out_filename)
                                with open(out_path, "wb") as f:
                                    f.write(data)
                                downloaded_files.append(out_path)
                                print(f"✅ Saved extracted logo image to: {out_path}")
                                valid_logo_idx += 1

                    # Close lightbox
                    page.keyboard.press("Escape")
                    page.wait_for_timeout(1000)

            except Exception as ex:
                print(f"Error handling image {idx}: {ex}")
                page.keyboard.press("Escape")
                page.wait_for_timeout(1000)

        # Check for any document download cards in chat
        doc_download_btns = main_chat.locator("button[aria-label*='Download'], div[title*='Download'], span[data-icon='download']").all()
        print(f"Found {len(doc_download_btns)} document download buttons in main chat.")
        for b_idx, btn in enumerate(doc_download_btns):
            try:
                if btn.is_visible():
                    print(f"Clicking document download button {b_idx+1}...")
                    btn.click()
                    page.wait_for_timeout(3000)
            except Exception as e:
                pass

        page.wait_for_timeout(3000)
        print("Final list of files in DEST_DIR:", os.listdir(DEST_DIR))
        browser.close()

if __name__ == "__main__":
    main()
