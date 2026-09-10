---
name: pitch-deck-builder
description: "Ubah narasi pitch menjadi deck siap presentasi (.pptx via python-pptx, atau HTML on-brand via power-design). Skill 2 (Slide) dari Framework 3S. Gunakan setiap kali the owner minta dibuatkan pitch deck, company profile deck, investor deck, sales deck, atau proposal deck. Trigger: 'buatkan pitch deck', 'bikin pptx untuk pitching', 'generate slide dari narasi ini', 'buatkan slide-nya', 'S2 Framework 3S', 'buat investor deck', 'susun slide company profile'. Jika belum ada narasi terstruktur, tawarkan susun dulu lewat pitch-story. JANGAN gunakan untuk slide training/edukasi umum atau prototype produk interaktif (pakai prototype-simulator)."
---

# Pitch Deck Builder - Skill 2 dari Framework 3S

Mengubah narasi pitch (dari `pitch-story`, atau input langsung jika sudah terstruktur) menjadi deck yang siap dipresentasikan.

## Langkah 0: Pilih jalur output

Tanyakan ke the owner kalau belum jelas:

| Jalur | Kapan dipakai | Cara |
|---|---|---|
| **.pptx** | Deck akan diedit sendiri, dikirim sebagai lampiran, atau dipresentasikan dari PowerPoint | `python-pptx` (v1.0.2 terpasang) |
| **HTML on-brand** | Deck akan dikirim sebagai link, atau butuh kualitas visual tinggi | Panggil skill `power-design` |

Default ke **.pptx** untuk KGF, aGROWforests, dan Yayasan (audiens korporat/donor umumnya mengharapkan file yang bisa diedit dan diarsipkan). Default ke **HTML on-brand** kalau the owner menyebut deck akan dikirim sebagai link atau minta kualitas visual tinggi.

## Alur kerja

1. **Cek apakah narasi sudah ada.** Kalau datang dari `pitch-story`, gunakan blok yang sudah disusun. Kalau langsung minta slide tanpa narasi, tanyakan singkat: entitas mana, siapa audiensnya, dan satu hal yang ingin dicapai. Lalu susun kerangka ringkas sebelum lanjut.
   - **Kalau ada tag `[BUKTI BELUM ADA]`:** JANGAN diam-diam diisi angka karangan, dan jangan dihilangkan. Tanyakan ke the owner apakah datanya sudah tersedia. Kalau belum, bawa slide itu dengan placeholder yang jelas ditandai, atau lewati sesuai poin 8 di bawah.
2. **Konfirmasi entitas dan bahasa** (lihat tabel routing di `pitch-story`). KGF dan aGROWforests dalam English. Pevesindo dan Yayasan dalam Indonesian. Jangan campur konteks KGF dengan Pevesindo.
3. **Pilih struktur slide** sesuai jenis pitch.
4. **Petakan tiap blok narasi ke 1-2 slide.** Jangan menjejalkan satu blok jadi satu slide penuh teks.
5. **Bangun deck**, simpan ke `Clients/<entitas>/pitch/` atau lokasi yang the owner tentukan.

## Struktur slide standar (10-12 slide)

Kerangka default, sesuaikan urutan dan jumlah:

1. **Cover** - Nama entitas, satu baris tagline yang menyampaikan transformasi (bukan nama lini bisnis), nama presenter.
2. **Problem** - Satu masalah tajam, didukung 1 angka/fakta yang membuatnya nyata.
3. **Agitate / Konsekuensi** - Apa yang terjadi kalau masalah dibiarkan (biaya, waktu, risiko regulasi, peluang hilang).
4. **Solusi / Transformasi** - Kondisi "sebelum vs sesudah", bukan daftar fitur teknis.
5. **Cara Kerja** - 3-4 langkah ringkas bagaimana solusi bekerja. Diagram atau ikon lebih baik dari paragraf.
6. **Market & Ukuran Peluang** *(investor deck)* - TAM/SAM/SOM jika tersedia, atau ukuran pasar yang bisa diverifikasi.
7. **Model Bisnis** - Bagaimana ini menghasilkan uang, satu kalimat + 1 diagram sederhana.
8. **Bukti / Traksi** - Angka, studi kasus, testimoni bernama, sertifikasi. Kalau belum ada data nyata, JANGAN mengarang. Gunakan placeholder bertanda jelas atau lewati slide ini.
9. **Kompetisi / Diferensiasi** *(opsional, untuk audiens sadar-solusi ke atas)* - Kenapa mekanisme ini berbeda, bukan cuma "lebih murah atau lebih cepat".
10. **Tim** *(investor deck)* - Kredibilitas singkat orang kunci.
11. **Tawaran / Ask** - Apa yang diminta secara spesifik + langkah berikutnya yang konkret. Untuk company profile yang tujuannya memancing minat, ask-nya adalah "hubungi kami / jadwalkan diskusi" dan harus tetap eksplisit dengan jalur kontak yang jelas, bukan tersirat.
12. **Kontak / Penutup** - Cara dihubungi, satu kalimat penutup yang mengingatkan transformasi inti.

### Varian per audiens

- **Buyer korporat / B2B (Verstegen, buyer EU):** ganti slide 6 (Market) dan 10 (Tim) dengan **Studi Kasus Relevan** dan **Rencana Implementasi / Timeline**. Audiens ini lebih peduli risiko eksekusi daripada ukuran pasar.
- **Donor / lembaga (GIZ, P4F, funder):** ganti slide 6 dan 7 dengan **Tata Kelola & Akuntabilitas** dan **Dampak Terukur**. Tambahkan slide kepatuhan (EUDR, sertifikasi, audit) kalau relevan.
- **Distributor / kontraktor (Pevesindo):** ganti slide 6 dan 10 dengan **Katalog & Spesifikasi Produk** dan **Dukungan Distribusi** (stok, lead time, jaringan, garansi).

## Prinsip desain slide pitch

- **Satu ide per slide.** Kalau ada dua ide penting, itu dua slide.
- **Headline slide = kesimpulan, bukan judul topik.** Bukan "Market Size" tapi "Pasar ini tumbuh 3x dalam 2 tahun terakhir". Pembaca yang cuma scroll cepat tetap dapat pesannya.
- **Angka besar, konteks kecil.** Kalau ada satu angka kuat, jadikan elemen visual utama slide, bukan tersembunyi di paragraf.
- **Teks minimal, bukan nol.** Deck yang dikirim tanpa presenter tetap butuh cukup teks untuk berdiri sendiri. Tanyakan konteks ini kalau belum jelas.
- **Batas teks per slide** - maksimal sekitar 40 kata untuk deck yang dibacakan presenter, sekitar 80 kata untuk deck yang dibaca sendiri. Ini kalibrasi, bukan aturan kaku. Kalau draft jauh melebihi, pecah jadi slide tambahan.

## Identitas visual

**Jangan menebak palet baru setiap kali.** Urutan penentuan:

1. Kalau the owner punya brand guideline atau logo untuk entitas itu, pakai itu.
2. Kalau belum ada, tanyakan dan tawarkan untuk mengunci satu palet per entitas agar konsisten lintas dokumen.
3. Kalau the owner minta jalur `power-design`, cek dulu `.agent/skills/power-design/brands/` untuk brand DNA yang sudah tersedia, atau gunakan `_template.md` untuk mendefinisikan brand entitas yang baru.

Arah umum kalau belum ada apa-apa: KGF, aGROWforests, dan Yayasan condong ke warna dalam/netral dengan satu aksen (audiens korporat, donor, institusi). Pevesindo boleh lebih berani sesuai kategori material interior. Konfirmasi sebelum mengunci.

## Sebelum menyerahkan

- Cek ulang tidak ada angka karangan yang menyusup menggantikan `[BUKTI BELUM ADA]`.
- Cek bahasa sudah sesuai entitas.
- Cek tidak ada pencampuran konteks KGF dengan Pevesindo.
- Cek tidak ada em-dash (aturan harness).
- Kalau deck menjelaskan metodologi atau proses internal yang bernilai komersial sebagai bagian "Cara Kerja", tanyakan ke the owner apakah tingkat detailnya sudah pas atau justru membuka terlalu banyak.

## Setelah selesai

Laporkan lokasi file. Ingatkan bahwa deck ini bisa dipasangkan dengan Skill 3 (`prototype-simulator`) kalau pitch melibatkan demo produk seperti TAPAK. Deck kuat plus prototype yang bisa diklik jauh lebih meyakinkan daripada deck saja.
