import sys
import os
import time
import base64
from playwright.sync_api import sync_playwright

KTP_DIR = "/mnt/c/Users/rifra/Downloads/KTP Enum Mutiara"
KK_DIR = "/mnt/c/Users/rifra/Downloads/KK Enum Mutiara"

os.makedirs(KTP_DIR, exist_ok=True)
os.makedirs(KK_DIR, exist_ok=True)

def main():
    with sync_playwright() as p:
        user_data_dir = os.path.expanduser("~/.config/antigravity-chrome-data")
        browser = p.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=False,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            args=["--disable-gpu", "--no-sandbox", "--disable-dev-shm-usage"]
        )
        page = browser.pages[0] if browser.pages else browser.new_page()
        page.goto("https://web.whatsapp.com")
        print("Navigated to WhatsApp Web...")
        
        # Wait for chat UI to be ready
        for i in range(25):
            time.sleep(3)
            if page.locator("header, div[role='grid']").count() > 0:
                print(f"Chat UI ready after {(i+1)*3}s!")
                break

        page.wait_for_timeout(2000)

        # Focus search box using Ctrl+F or click
        print("Focusing search box and typing 'Heriadi'...")
        page.keyboard.press("Control+f")
        page.wait_for_timeout(1000)
        page.keyboard.type("Heriadi")
        page.wait_for_timeout(4000)

        page.screenshot(path="scratch/wa_heriadi_search_result.png")

        # Click on Heriadi contact
        heriadi = page.locator("span[title*='Heriadi'], span[title*='heriadi']").first
        if not heriadi.is_visible():
            heriadi = page.get_by_text("Heriadi").first

        if not heriadi or not heriadi.is_visible():
            print("Trying search for 'Heri'...")
            page.keyboard.press("Control+a")
            page.keyboard.press("Backspace")
            page.keyboard.type("Heri")
            page.wait_for_timeout(3000)
            heriadi = page.locator("span[title*='Heri'], span[title*='heri']").first

        if heriadi and heriadi.is_visible():
            print("Found Heriadi! Opening chat...")
            heriadi.click(force=True)
            page.wait_for_timeout(3000)
        else:
            print("Contact 'Heriadi' not found in search results.")
            page.screenshot(path="scratch/wa_heriadi_not_found.png")
            browser.close()
            return

        page.screenshot(path="scratch/wa_heriadi_chat_opened.png")

        # Download listener
        downloaded = []
        def handle_download(dl):
            fn = dl.suggested_filename
            fn_lower = fn.lower()
            if "kk" in fn_lower:
                target = os.path.join(KK_DIR, fn)
            else:
                target = os.path.join(KTP_DIR, fn)
            dl.save_as(target)
            downloaded.append(target)
            print(f"✅ DOWNLOADED FILE FROM HERIADI: {target}")

        page.on("download", handle_download)

        # Scroll up in Heriadi chat history
        main_chat = page.locator("#main").first
        if not main_chat.is_visible():
            main_chat = page.locator("div[role='region']").first

        print("Scrolling up in Heriadi chat history...")
        for _ in range(8):
            main_chat.focus()
            page.keyboard.press("PageUp")
            page.wait_for_timeout(1000)

        page.screenshot(path="scratch/wa_heriadi_history.png")

        # Download documents/attachments
        doc_cards = main_chat.locator("div[role='button'], button[aria-label*='Download'], div[title*='Download'], span[data-icon='download']").all()
        print(f"Found {len(doc_cards)} potential download elements in Heriadi chat.")

        for b_idx, btn in enumerate(doc_cards):
            try:
                txt = btn.inner_text().lower()
                title = (btn.get_attribute("title") or btn.get_attribute("aria-label") or "").lower()
                if any(k in txt or k in title for k in ['ktp', 'kk', 'fadhilah', 'kurniawan', 'duta', 'febi', 'taufik', 'ruly', 'pdf', 'png', 'jpg', 'jpeg', 'download']):
                    print(f"Clicking attachment/download item {b_idx+1}: {txt[:40]}")
                    btn.click(force=True)
                    page.wait_for_timeout(2000)
            except Exception as e:
                pass

        # Extract blob images in Heriadi chat
        imgs = main_chat.locator("img[src^='blob:']").all()
        print(f"Found {len(imgs)} blob images in Heriadi chat.")
        for idx, img in enumerate(imgs):
            try:
                src = img.get_attribute("src")
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
                }""", src)

                if data_url and "," in data_url:
                    header_str, encoded = data_url.split(",", 1)
                    ext = "png"
                    if "jpeg" in header_str or "jpg" in header_str:
                        ext = "jpg"
                    data = base64.b64decode(encoded)
                    out_path = os.path.join(KTP_DIR, f"Heriadi_Doc_{idx+1}.{ext}")
                    with open(out_path, "wb") as f:
                        f.write(data)
                    print(f"✅ Saved Heriadi image: {out_path} ({len(data)} bytes)")
            except Exception as e:
                pass

        page.wait_for_timeout(3000)
        print(f"Done! Total files downloaded from Heriadi: {len(downloaded)}")
        browser.close()

if __name__ == "__main__":
    main()
