from playwright.sync_api import sync_playwright

def main():
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp("http://localhost:9222")
        context = browser.contexts[0]
        page = context.pages[0] if context.pages else context.new_page()
        
        # Ambil tangkapan layar penuh saat ini (tanpa navigasi, untuk melihat state aslinya)
        page.screenshot(path="scratch/wa_state.png", full_page=True)
        
        # Simpan struktur DOM-nya sekalian
        with open("scratch/wa_dom.html", "w", encoding="utf-8") as f:
            f.write(page.content())
            
        print("Tangkapan layar dan DOM berhasil diambil!")
        browser.disconnect()

if __name__ == "__main__":
    main()
