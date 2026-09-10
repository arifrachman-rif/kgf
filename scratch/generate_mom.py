import sys
import json
import urllib.request
import os

sys.path.append("meeting-recorder")
from common import load_gemini_key

GEMINI_BASE = "https://generativelanguage.googleapis.com"

def main():
    key = load_gemini_key()
    
    t1_path = "scratch/mutiara_transcript_1.md"
    t2_path = "scratch/mutiara_transcript_2.md"
    
    with open(t1_path, "r", encoding="utf-8") as f:
        t1 = f.read()
    with open(t2_path, "r", encoding="utf-8") as f:
        t2 = f.read()
        
    transcript = f"--- PART 1 ---\n{t1}\n\n--- PART 2 ---\n{t2}"
    
    prompt = """Berdasarkan transkrip rapat Yayasan Mutiara Nusa Antara berikut, buatlah dokumen Minutes of Meeting (MoM) yang komprehensif, profesional, dan berorientasi pada aksi.

Struktur MoM yang diharapkan:
# Minutes of Meeting: Yayasan Mutiara Nusa Antara

## 1. Informasi Rapat
- (Tarik konteks waktu/tanggal/agenda jika tersirat)

## 2. Poin-Poin Pembahasan Utama
- (Kelompokkan berdasarkan topik yang dibahas, bukan sekadar kronologis)
- (Sertakan keputusan penting yang diambil)

## 3. Action Items (Tindak Lanjut)
- (Buat dalam bentuk tabel atau bullet points: Siapa melakukan Apa dan Kapan)

## 4. Kendala & Catatan Khusus
- (Tuliskan masalah birokrasi, sistem, atau operasional yang mengemuka, misalnya masalah perizinan di Lampung/BPN, dll)

Gunakan bahasa Indonesia yang baku, profesional, dan mudah dipahami.
Tulis dalam format Markdown yang rapi.

--- TRANSKRIP RAPAT ---
"""
    
    body = {
        "contents": [{"parts": [{"text": prompt + transcript}]}],
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 8192}
    }
    
    print("Menganalisis transkrip dan menyusun MoM...")
    req = urllib.request.Request(
        f"{GEMINI_BASE}/v1beta/models/gemini-flash-latest:generateContent",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "x-goog-api-key": key},
        method="POST"
    )
    
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            data = json.loads(r.read())
            
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        out_file = "scratch/MOM_Yayasan_Mutiara_Nusa_Antara.md"
        with open(out_file, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"DONE: MoM berhasil disimpan ke {out_file}")
    except Exception as e:
        print(f"Error: {e}")
        if hasattr(e, 'read'):
            print(e.read().decode())

if __name__ == "__main__":
    main()
