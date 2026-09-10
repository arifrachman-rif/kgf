import requests

res = requests.get("https://www.pevesindo.co.id/")
text = res.text.lower()
idx = text.find("hommilux")

if idx != -1:
    print("DITEMUKAN pada karakter ke:", idx)
    print("Konteks sekitarnya:")
    # Print 200 karakter sebelum dan sesudah
    start = max(0, idx - 200)
    end = min(len(text), idx + 200)
    print(res.text[start:end])
else:
    print("Tidak ditemukan sama sekali.")
