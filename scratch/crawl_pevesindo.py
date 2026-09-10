import requests
import re
from urllib.parse import urljoin, urlparse
from urllib.parse import urljoin, urlparse

def crawl_and_search(base_url, keyword):
    print(f"\nMulai memindai {base_url}...")
    try:
        response = requests.get(base_url, timeout=10)
        response.raise_for_status()
    except Exception as e:
        print(f"Gagal mengakses {base_url}: {e}")
        return []


    
    # Cari di beranda dulu
    found_urls = set()
    if keyword.lower() in response.text.lower():
        print(f"[!] DITEMUKAN di beranda: {base_url}")
        found_urls.add(base_url)
        
    # Ambil semua link internal menggunakan regex
    internal_links = set()
    links = re.findall(r'href=[\'"]([^\'"]+)[\'"]', response.text)
    
    for href in links:
        full_url = urljoin(base_url, href)
        parsed_url = urlparse(full_url)
        
        # Filter hanya link internal yang valid dan bukan link anchor (#) di halaman yang sama
        if parsed_url.netloc == urlparse(base_url).netloc and '#' not in href and not href.startswith('mailto:') and not href.startswith('tel:'):
            # Jangan crawl wp-content, feed, xml
            if '/wp-content/' not in full_url and '/feed/' not in full_url and not full_url.endswith('.xml'):
                internal_links.add(full_url)
                
    print(f"Ditemukan {len(internal_links)} sub-halaman internal.")
    
    # Kunjungi tiap sub-halaman
    for url in list(internal_links)[:20]: # Batasi 20 halaman utama agar cepat
        try:
            res = requests.get(url, timeout=10)
            if keyword.lower() in res.text.lower():
                print(f"[!] DITEMUKAN di {url}")
                found_urls.add(url)
        except Exception as e:
            pass
            
    if not found_urls:
        print("[-] BERSIH. Tidak ditemukan kata hommilux di struktur utama situs.")
        
    return list(found_urls)

if __name__ == "__main__":
    import urllib3
    urllib3.disable_warnings()
    
    keyword = "hommilux"
    sites = [
        "https://www.pevesindo.co.id/",
        "https://www.pevesindo.com/"
    ]
    
    results = {}
    for site in sites:
        res = crawl_and_search(site, keyword)
        results[site] = res
        
    print("\n\n--- KESIMPULAN ---")
    with open("scratch/laporan_pevesindo.txt", "w") as f:
        f.write("Laporan Pemindaian Situs Pevesindo:\n\n")
        for site, links in results.items():
            if links:
                msg = f"❌ {site}: Ditemukan sisa 'hommilux' di halaman berikut:\n" + "\n".join(f"  - {l}" for l in links)
            else:
                msg = f"✅ {site}: BERSIH dari kata 'hommilux' di halaman utama dan struktur."
            print(msg)
            f.write(msg + "\n\n")
