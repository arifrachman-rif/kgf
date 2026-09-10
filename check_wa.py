import sys
from playwright.sync_api import sync_playwright

def check_wa():
    p = sync_playwright().start()
    print("Menghubungkan ke CDP...", file=sys.stderr)
    try:
        browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        context = browser.contexts[0]
        
        wa_page = None
        for page in context.pages:
            print(f"Tab terbuka: {page.url}")
            if "whatsapp.com" in page.url.lower():
                wa_page = page
                break
                
        if not wa_page:
            print("WhatsApp tidak terbuka di tab manapun.")
            sys.exit(1)
            
        print("WhatsApp tab ditemukan. Mengecek status login...")
        
        # Cek apakah ada elemen qr atau chat
        wa_page.wait_for_timeout(2000)
        content = wa_page.content()
        if "QR code" in content or "Scan me" in content:
            print("STATUS: Belum Login (Menunggu QR Code)")
        elif "Search" in content or "Chat" in content or wa_page.get_by_role("textbox").count() > 0:
            print("STATUS: Logged In / Siap digunakan")
        else:
            print("STATUS: Tidak diketahui (Mungkin sedang loading)")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        try:
            browser.close()
        except:
            pass
        p.stop()

if __name__ == "__main__":
    check_wa()
