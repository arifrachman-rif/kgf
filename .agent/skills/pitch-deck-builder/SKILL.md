---
name: pitch-deck-builder
description: "Ubah narasi pitch menjadi file .pptx pitch deck yang siap presentasi. Ini adalah Skill 2 (Slide) dari Framework 3S (Story-Slide-Simulate) — dipakai setelah narasi pitch tersusun (lihat skill pitch-story untuk Skill 1). WAJIB gunakan setiap kali user minta dibuatkan pitch deck, investor deck, sales deck, atau proposal deck dalam format PowerPoint/.pptx. Trigger pada: 'buatkan pitch deck', 'bikin pptx untuk pitching', 'generate slide dari narasi ini', 'S2 Framework 3S', 'buat investor deck', 'susun slide presentasi ke klien'. Jika user belum punya narasi terstruktur, tawarkan untuk menyusunnya dulu lewat pitch-story sebelum lanjut ke slide — jangan langsung generate slide dari ide mentah tanpa struktur. JANGAN gunakan untuk slide edukasi/training umum yang bukan pitch (pakai skill pptx biasa) atau untuk prototype produk interaktif (pakai prototype-simulator)."
---

# Pitch Deck Builder — Skill 2 dari Framework 3S

Mengubah narasi pitch (dari `pitch-story`, atau dari input user langsung jika sudah terstruktur) menjadi file `.pptx` yang siap dipresentasikan. Skill ini adalah lapisan **struktur pitch deck** di atas skill `pptx` bawaan — baca dulu `/mnt/skills/public/pptx/SKILL.md` untuk mekanisme teknis pembuatan file PowerPoint (layout, font, tabel, dsb), lalu terapkan struktur khusus pitch deck di bawah ini.

## Alur kerja

1. **Cek apakah narasi sudah ada.** Jika user datang langsung dari `pitch-story`, gunakan blok-blok yang sudah disusun (Problem/Agitate/Transformation/Market/Model Bisnis/Offer). Jika user langsung minta slide tanpa narasi terstruktur, tanyakan singkat: siapa audiensnya, dan apa satu hal yang ingin dicapai dari pitch ini — lalu susun kerangka ringkas sebelum lanjut ke slide.
   - **Kalau ada tag `[BUKTI BELUM ADA]` di narasi yang diterima:** JANGAN diam-diam diisi dengan angka/klaim karangan, dan jangan dihilangkan begitu saja. Tanyakan ke user apakah datanya sudah tersedia sekarang; kalau belum, bawa slide tersebut dengan placeholder yang jelas ditandai (bukan angka fiktif), atau lewati slide itu sesuai instruksi di poin 8 struktur slide.
2. **Pilih struktur slide** sesuai jenis pitch (lihat di bawah).
3. **WAJIB: tunjukkan outline dulu, minta persetujuan, baru render.** Sebelum menyentuh python-pptx, sajikan tabel outline: nomor slide → judul assertion (kalimat kesimpulan lengkap, bukan topik) → jenis visual yang diusulkan (chart/diagram proses/angka besar/foto) → blok narasi sumbernya. Alasannya ekonomis: merevisi outline butuh dua menit, merevisi file jadi butuh dua puluh. Baru lanjut render setelah user menyetujui atau merevisi outline. Kecuali user secara eksplisit minta langsung jadi tanpa review, langkah ini tidak boleh dilewati.
4. **Baca `/mnt/skills/public/pptx/SKILL.md`** untuk teknik pembuatan file — python-pptx, layout, tipografi, palet warna, ekspor.
5. **Petakan tiap blok narasi ke 1-2 slide.** Jangan menjejalkan satu blok narasi jadi satu slide penuh teks — pecah kalau perlu.
6. **Masukkan baris transisi narasi sebagai speaker notes.** Setiap blok narasi dari `pitch-story` punya baris transisi — tempatkan sebagai catatan pembicara (notes) di slide terkait via python-pptx (`slide.notes_slide.notes_text_frame.text`), plus inti pesan bloknya. Deck yang punya speaker notes siap dibacakan tanpa menghafal; deck tanpa notes memaksa presenter membaca slide-nya sendiri.
7. **Bangun deck**, simpan ke `/mnt/user-data/outputs/`, dan **tawarkan versi PDF** untuk dikirim sebagai bahan baca awal (pre-meeting) via WA/email — praktik dua-format (.pptx untuk presentasi + PDF untuk dikirim) terbukti membuat audiens datang ke meeting sudah setengah paham.

## Struktur slide standar (10-12 slide)

Gunakan sebagai kerangka default, sesuaikan urutan/jumlah sesuai konteks:

1. **Cover** — Nama bisnis/produk, satu baris tagline yang menyampaikan transformasi (bukan nama fitur), nama presenter.
2. **Problem** — Satu masalah tajam, didukung 1 angka/fakta yang membuatnya nyata.
3. **Agitate / Konsekuensi** — Apa yang terjadi kalau masalah ini dibiarkan (biaya, waktu, peluang hilang).
4. **Solusi / Transformasi** — Kondisi "sebelum vs sesudah", bukan daftar fitur teknis.
5. **Cara Kerja** — 3-4 langkah ringkas bagaimana solusi bekerja (diagram/ikon lebih baik dari paragraf).
6. **Market & Ukuran Peluang** *(khusus investor deck)* — TAM/SAM/SOM jika tersedia, atau ukuran pasar yang bisa diverifikasi.
7. **Model Bisnis** — Bagaimana produk ini menghasilkan uang, dalam satu kalimat + 1 diagram sederhana.
8. **Bukti / Traksi** — Angka, studi kasus, atau testimoni bernama. Jika belum ada data nyata, JANGAN mengarang angka — gunakan placeholder yang jelas ditandai untuk diisi user, atau lewati slide ini.
9. **Kompetisi / Diferensiasi** *(opsional, untuk audiens sadar-solusi ke atas)* — Kenapa mekanisme ini berbeda, bukan cuma "lebih murah/lebih cepat".
10. **Tim** *(untuk investor deck)* — Kredibilitas singkat orang-orang kunci.
11. **Tawaran / Ask** — Apa yang diminta secara spesifik (investasi, budget, tanda tangan kontrak) + langkah berikutnya yang konkret.
12. **Kontak / Penutup** — Cara dihubungi, satu kalimat penutup yang mengingatkan transformasi inti.

**Untuk pitch ke klien korporat/B2B** (bukan investor): ganti slide 6 (Market) dan 10 (Tim) dengan **Studi Kasus Relevan** dan **Rencana Implementasi/Timeline** — audiens B2B korporat lebih peduli risiko eksekusi daripada ukuran pasar.

## Prinsip desain slide pitch

- **Satu ide per slide** (Cognitive Load Theory, Sweller): setiap elemen tidak perlu mencuri kapasitas pemahaman audiens. Kalau ada dua ide penting, itu dua slide.
- **Headline slide = kesimpulan, bukan judul topik** (Assertion-Evidence, Alley/Penn State). Bukan "Market Size" tapi "Pasar ini tumbuh 3x dalam 2 tahun terakhir" — pembaca yang hanya scroll cepat tetap dapat pesannya, dan isi slide menjadi bukti visual atas klaim di judul.
- **Setiap slide isi punya satu elemen visual bermakna** (Dual Coding + Picture Superiority): angka dan proses kunci tampil sebagai diagram/chart, bukan paragraf. Jenis visualnya sudah ditentukan di outline (langkah 3) — jangan diputuskan dadakan saat render. Visual dekoratif tanpa fungsi bukan pengganti.
- **Angka besar, konteks kecil.** Kalau ada satu angka kuat, buat dia jadi elemen visual utama slide, bukan tersembunyi di paragraf.
- **Teks minimal, bukan nol.** Pitch deck yang dikirim tanpa presenter (dibaca sendiri oleh investor/klien) tetap butuh cukup teks untuk berdiri sendiri — beda dengan slide yang akan dibacakan langsung. Tanyakan konteks ini ke user jika belum jelas.
- **Konsisten dengan identitas visual** — jika user punya warna brand/logo, gunakan; jika tidak, pilih palet yang sesuai audiens (korporat = warna dalam/netral + satu aksen; startup consumer = lebih berani). Untuk pitch atas nama Sam Ipoel/ANABA tanpa identitas visual lain yang diminta, default ke sistem visual established: near-black `#0B0B0A`, mint `#3FBF6F`, rust `#C8500F`, cream `#F2E8DC`, dengan Fraunces (display), IBM Plex Mono (label), Plus Jakarta Sans (body) — jangan tebak palet baru tiap kali kalau ini konteksnya.
- **Batas teks per slide** — maksimal ±40 kata per slide untuk deck yang akan dibacakan presenter langsung, ±80 kata untuk deck yang dikirim untuk dibaca sendiri (lihat poin "Teks minimal, bukan nol" di atas untuk cara menentukan mana yang berlaku). Ini batas kalibrasi, bukan aturan kaku — tapi kalau draft jauh melebihi ini, pecah jadi slide tambahan.

## Sebelum menyerahkan: cek risiko bocor metodologi

Kalau deck ini menjelaskan **metodologi berbayar Anda sendiri** (Framework 3S, TRACE-Q, PSME, dsb.) sebagai bagian dari "Cara Kerja" — terutama untuk pitch yang tujuannya menjual training/konsultasi tentang metodologi itu sendiri — cek dulu apakah slide "Cara Kerja" membocorkan detail Lapis 2-3 (parameter, ambang kalibrasi, langkah teknis presisi) yang seharusnya jadi bahan berbayar. Kalau ragu, tawarkan ke user untuk jalankan `secret-sauce-guard` terhadap draft sebelum finalisasi.

## Setelah selesai

Simpan file ke `/mnt/user-data/outputs/`, gunakan `present_files` untuk menyerahkannya. Ingatkan user bahwa slide ini siap dipraktikkan bersama Skill 3 (`prototype-simulator`) kalau pitch mereka melibatkan demo produk — deck yang kuat + prototype yang bisa diklik biasanya jauh lebih meyakinkan daripada deck saja.
