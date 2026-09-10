from playwright.sync_api import sync_playwright

def main():
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp("http://localhost:9222")
        context = browser.contexts[0]
        page = context.pages[0]
        
        # Coba berbagai cara untuk klik tombol Attach
        attach_btn = None
        
        selectors = [
            'div[title="Attach"]',
            'div[aria-label="Attach"]',
            'span[data-icon="plus"]',
            'span[data-icon="clip"]'
        ]
        
        for sel in selectors:
            loc = page.locator(sel).first
            if loc.is_visible():
                print(f"FOUND: {sel}")
                attach_btn = loc
                break
                
        if not attach_btn:
            print("TIDAK MENEMUKAN TOMBOL ATTACH DENGAN SELECTOR STANDAR")
            # Coba cari tombol di sebelah kiri textbox
            tb = page.get_by_role("textbox").last
            # ini sulit di-query tanpa DOM yang jelas, kita dump saja isi HTML dari parent-nya
            print(tb.evaluate('el => el.parentElement.parentElement.parentElement.outerHTML')[:1000])
        else:
            attach_btn.click()
            page.wait_for_timeout(2000)
            print("KLIK BERHASIL. Mencari tombol Document...")
            doc_btn = page.locator('span:has-text("Document")').first
            if not doc_btn.is_visible():
                doc_btn = page.locator('li:has-text("Document")').first
            
            if doc_btn.is_visible():
                print("TOMBOL DOCUMENT DITEMUKAN!")
            else:
                print("TOMBOL DOCUMENT TIDAK DITEMUKAN!")

if __name__ == "__main__":
    main()
