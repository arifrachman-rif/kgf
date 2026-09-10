from playwright.sync_api import sync_playwright

def main():
    with sync_playwright() as p:
        try:
            browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
            context = browser.contexts[0] if browser.contexts else browser.new_context()
            page = context.pages[0] if context.pages else context.new_page()
            html = page.content()
            with open("whatsapp_dom.html", "w", encoding="utf-8") as f:
                f.write(html)
            browser.disconnect()
            print("Successfully dumped DOM to whatsapp_dom.html")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    main()
