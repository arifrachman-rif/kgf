from playwright.sync_api import sync_playwright

def main():
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp("http://localhost:9222")
        context = browser.contexts[0]
        page = context.pages[0]
        
        print("--- ARIA LABELS ---")
        elements = page.locator('[aria-label]').all()
        labels = set()
        for el in elements:
            try: labels.add(el.get_attribute("aria-label"))
            except: pass
        for l in sorted(list(labels)):
            print(l)
            
        print("\n--- TITLES ---")
        elements = page.locator('[title]').all()
        titles = set()
        for el in elements:
            try: titles.add(el.get_attribute("title"))
            except: pass
        for t in sorted(list(titles)):
            print(t)

if __name__ == "__main__":
    main()
