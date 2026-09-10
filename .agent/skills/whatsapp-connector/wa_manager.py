import argparse
import sys
import time
from playwright.sync_api import sync_playwright

WA_URL = "https://web.whatsapp.com"

def connect_browser():
    p = sync_playwright().start()
    print("Menghubungkan ke peladen CDP latar belakang...", file=sys.stderr)
    try:
        browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        context = browser.contexts[0]
        # Cari tab yang sudah membuka WhatsApp
        page = None
        for pg in context.pages:
            if "whatsapp" in pg.url.lower():
                page = pg
                break
        
        if not page:
            page = context.pages[0] if context.pages else context.new_page()
            page.goto(WA_URL)
            
        return p, browser, page
    except Exception as e:
        print(f"Gagal terhubung ke CDP Server: {e}", file=sys.stderr)
        print("Pastikan peladen browser-service sudah berjalan (via wsl xvfb-run -a python3 ...)", file=sys.stderr)
        sys.exit(1)

def cmd_send(to, message, file_path=""):
    print("Menjalankan WhatsApp Connector V2 (CDP Mode)...", file=sys.stderr)
    p, browser, page = connect_browser()
    try:
        # Jika belum termuat sempurna, tunggu sebentar
        if "whatsapp" not in page.url.lower():
            page.goto(WA_URL)
            
        print("Memastikan antarmuka siap (seharusnya instan karena tersinkronisasi)...", file=sys.stderr)
        
        # Penetrasi Shadow DOM milik engine Lexical (Meta)
        textboxes = page.get_by_role("textbox")
        textboxes.first.wait_for(state="visible", timeout=60000)
        
        print(f"Mencari kontak: {to}", file=sys.stderr)
        textboxes.first.fill(to)
        page.wait_for_timeout(2000)
        
        contact = page.get_by_title(to).first
        if not contact.is_visible():
            contact = page.get_by_text(to).first
            
        contact.wait_for(state="visible", timeout=15000)
        contact.click()
        
        print("Chat ditemukan. Mengetik pesan...", file=sys.stderr)
        page.wait_for_timeout(2000)
        
        message_box = textboxes.last
        if message:
            message_box.fill(message)
            message_box.press("Enter")
            print("PESAN BERHASIL DIKIRIM!", file=sys.stderr)
            page.wait_for_timeout(3000)
            
        if file_path:
            print(f"Melampirkan file: {file_path}", file=sys.stderr)
            # Menggunakan UI click untuk menghindari error file not supported dari hidden input
            page.locator('button[aria-label="Attach"]').click()
            
            # Tunggu sampai teks Document muncul di menu pop-up
            doc_btn = page.locator('text="Document"').last
            doc_btn.wait_for(state="visible", timeout=10000)
                
            with page.expect_file_chooser() as fc_info:
                doc_btn.click()
                
            file_chooser = fc_info.value
            file_chooser.set_files(file_path)
            page.wait_for_timeout(3000)
            
            send_btn = page.locator('div[aria-label="Send"]')
            if send_btn.is_visible():
                send_btn.click()
            else:
                page.keyboard.press("Enter")
                
            print("FILE BERHASIL DIKIRIM!", file=sys.stderr)
            page.wait_for_timeout(5000)
    except Exception as e:
        print(f"Error saat mengirim pesan: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        browser.close()
        p.stop()

def main():
    parser = argparse.ArgumentParser(description="WhatsApp CLI Connector V2")
    subparsers = parser.add_subparsers(dest="command")
    
    send_parser = subparsers.add_parser("send", help="Kirim pesan otomatis via CDP")
    send_parser.add_argument("--to", required=True, help="Nama Kontak atau Grup")
    send_parser.add_argument("--message", required=False, default="", help="Isi pesan teks")
    send_parser.add_argument("--file", required=False, default="", help="Path file untuk dilampirkan")
    
    args = parser.parse_args()
    
    if args.command == "send":
        cmd_send(args.to, args.message, args.file)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
