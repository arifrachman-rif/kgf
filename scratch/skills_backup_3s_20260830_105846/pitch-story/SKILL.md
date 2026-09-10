---
name: pitch-story
description: "Susun narasi pitch yang meyakinkan untuk company profile, pitch deck, atau proposal bisnis - sebelum satu slide pun dibuat. Skill 1 (Story) dari Framework 3S (Story-Slide-Simulate). Gunakan setiap kali the owner ingin membuat pitch deck, company profile, presentasi ke investor/klien/donor, atau proposal bisnis - bahkan jika langsung minta 'buatkan slide-nya', tawarkan dulu susun narasi lewat skill ini sebelum lanjut ke pitch-deck-builder. Trigger: 'buat narasi pitch', 'susun cerita untuk pitch deck', 'company profile', 'profil perusahaan', 'bikin story untuk presentasi ke investor', 'pitch story', 'S1 Framework 3S', 'gimana cara jelasin bisnis ini biar meyakinkan'. JANGAN gunakan untuk PRD (pakai prd-pipeline) atau weekly report (pakai weekly-report-generator)."
---

# Pitch Story - Skill 1 dari Framework 3S

Susun argumen pitch lebih dulu, sebelum desain, sebelum slide. Output skill ini adalah **naskah narasi terstruktur** yang siap diteruskan ke `pitch-deck-builder` (Skill 2) atau dipakai langsung sebagai script bicara.

## Kenapa urutan ini penting

Kesalahan paling umum: buka PowerPoint dulu, baru mikir apa yang mau dikatakan. Hasilnya slide penuh bullet tapi tidak ada alur yang menggerakkan pendengar dari "belum peduli" ke "mau bertindak". Narasi kuat membuat slide sesederhana apapun tetap meyakinkan. Slide cantik tanpa narasi hanya terlihat rapi.

## Langkah 0: Gali konteks dulu

Sebelum menulis, tanyakan (singkat, jangan interogasi kalau the owner sudah kasih detail):

1. **Entitas mana?** Ini menentukan bahasa dan isi. Lihat tabel routing di bawah.
2. **Siapa yang akan mendengar/membaca?** Investor, buyer internasional, donor/lembaga, klien korporat, distributor, atau komunitas.
3. **Apa SATU tindakan yang diinginkan setelah pitch selesai?** Untuk company profile yang tujuannya memancing minat, ask-nya biasanya "hubungi kami / jadwalkan diskusi" - itu tetap satu ask yang sah, dan harus eksplisit, bukan tersirat.
4. **Apa bukti terkuat yang dimiliki?** Angka, studi kasus, hasil pilot, testimoni bernama, sertifikasi. Kalau belum ada, tandai sebagai gap. Jangan mengarang bukti.

### Routing entitas (WAJIB dicek, dari CLAUDE.md)

| Entitas | Bahasa | Audiens tipikal | Bukti yang paling menggerakkan |
|---|---|---|---|
| PT Klumbayan Gold Farm (KGF) | English | Buyer EU, donor, mitra konsorsium | Volume transaksi, jaringan petani, TAPAK, kesiapan EUDR, sertifikasi |
| aGROWforests | English | Konsorsium, buyer, funder | Restorasi lahan, ethical sourcing, traceability lintas mitra |
| Pevesindo (PT Alastri Teguh International) | Indonesian | Distributor, kontraktor, toko bangunan | Kapasitas produksi, katalog, jaringan distribusi, proyek terpasang |
| Yayasan (Insan Edukasi Indonesia / Cipta Generasi Qur'ani) | Indonesian | Donatur, mitra komunitas, pemda | Jumlah penerima manfaat, program berjalan, tata kelola |

**BATAS KERAS:** KGF dan Pevesindo tidak punya kegiatan yang berkaitan. Jangan pernah mencampur konteks, data, atau klaim keduanya dalam satu dokumen kecuali the owner secara eksplisit meminta.

## Langkah 1: Tentukan tahap kesadaran audiens

Metodologi Eugene Schwartz. Pilih SATU:

| Tahap | Kondisi audiens | Yang harus dilakukan narasi |
|---|---|---|
| Belum sadar masalah | Tidak merasa punya masalah ini | Buka dengan cerita/gejala, bukan produk |
| Sadar masalah | Tahu masalahnya, belum tahu solusinya | Perbesar konsekuensi, baru kenalkan kategori solusi |
| Sadar solusi | Tahu solusi jenis ini ada, belum pilih | Bedakan mekanisme, kenapa cara kita berbeda |
| Sadar produk | Tahu produk kita, belum putuskan | Perkuat bukti, tangani keberatan |
| Siap beli | Tinggal butuh dorongan terakhir | Langsung ke tawaran + langkah berikutnya |

Company profile yang disebar luas biasanya menyasar "sadar masalah" atau "sadar solusi". Pitch ke Verstegen atau mitra yang sudah beberapa kali diskusi biasanya "sadar produk". Salah menebak tahap ini adalah alasan #1 pitch yang sudah bagus tetap terasa hambar.

## Langkah 2: Bangun struktur narasi (PATO)

**Problem - Agitate - Transformation - Offer.** Adaptasi PAS klasik untuk format pitch 8-12 slide.

1. **Problem** - Satu kalimat tajam tentang masalah nyata yang dialami audiens atau target pasar mereka. Spesifik dan bisa dikenali, bukan generik.
2. **Agitate** - Perbesar konsekuensi kalau masalah dibiarkan. Angka kerugian, waktu terbuang, peluang hilang, risiko regulasi. Bagian paling sering dilewati padahal paling menggerakkan.
3. **Transformation** - Perkenalkan solusi BUKAN sebagai daftar fitur, tapi sebagai pergeseran kondisi "sebelum" ke "sesudah". Fitur disebut setelah transformasi jelas.
4. **Offer** - Tawaran konkret + bukti + langkah berikutnya, termasuk penanganan 1-2 keberatan paling umum secara proaktif.

**Kalibrasi Agitate per audiens.** Untuk donor, lembaga, dan buyer korporat, Agitate dibangun dari **risiko dan konsekuensi faktual** (kepatuhan EUDR, putusnya rantai pasok, kegagalan audit), bukan dari tekanan emosional atau urgensi buatan. Untuk audiens komunitas atau UMKM, ruang emosinya lebih lebar. Jangan pernah pakai deadline palsu atau kelangkaan karangan.

Blok tambahan di antara Transformation dan Offer, sesuai jenis pitch:
- **Investor/funder:** Market & Traction, lalu Model Bisnis.
- **Buyer korporat/B2B:** Studi Kasus Relevan, lalu Rencana Implementasi.
- **Donor/lembaga:** Tata Kelola & Akuntabilitas, lalu Dampak Terukur.

## Langkah 3: Tulis per-blok, bukan per-slide

Tulis sebagai naskah mengalir per blok. Nanti `pitch-deck-builder` yang memecahnya jadi slide. Untuk setiap blok tulis:
- **Inti pesan** (1 kalimat)
- **Bukti/detail pendukung** (2-4 kalimat, angka spesifik kalau ada. Kalau tidak ada, tandai `[BUKTI BELUM ADA]`, jangan mengarang)
- **Baris transisi** ke blok berikutnya (1 kalimat penghubung)

## Langkah 4: Uji dengan 4C sebelum diserahkan

- **Clear** - bisa dipahami tanpa penjelasan tambahan?
- **Concise** - bisa dipotong tanpa kehilangan makna?
- **Compelling** - ada alasan untuk peduli, bukan cuma informasi?
- **Credible** - akan dipercaya pendengar skeptis, atau terdengar seperti hype?

Untuk KGF dan aGROWforests, Credible adalah gerbang terberat. Dokumen ini bisa sampai ke auditor donor atau tim compliance buyer EU. Satu angka yang tidak bisa dipertanggungjawabkan merusak seluruh dokumen.

## Format output

Dokumen terstruktur dengan heading per blok (Problem / Agitate / Transformation / blok tambahan / Offer), masing-masing berisi Inti Pesan, Bukti Pendukung, dan Transisi. Tandai jelas di akhir dokumen bagian mana yang masih butuh data dari the owner (`[BUKTI BELUM ADA]`).

Contoh satu blok (kalibrasi format, bukan template isi):

```
### Problem
**Inti pesan:** Buyer EU tidak bisa membuktikan asal-usul lada dari petani kecil.
**Bukti pendukung:** [BUKTI BELUM ADA - minta angka rejection rate atau biaya audit dari the owner]
**Transisi:** Kalau ini dibiarkan sampai EUDR berlaku penuh...
```

Tutup dengan satu baris: **"Narasi ini siap dilanjutkan ke pembuatan slide - bilang 'buatkan slide-nya' untuk lanjut ke Skill 2."**

## Handoff ke Skill 2

`pitch-deck-builder` membaca output ini apa adanya sebagai sumber slide. Supaya handoff tidak ambigu lintas sesi:
- Pertahankan heading blok persis (Problem/Agitate/Transformation/dst). Jangan ganti nama blok di tengah dokumen.
- Setiap `[BUKTI BELUM ADA]` yang belum terisi HARUS tetap bertag persis. Ini yang membuat Skill 2 tahu harus tanya dulu, bukan lanjut generate dengan angka karangan.
- Catat entitas dan bahasa target di kepala dokumen, supaya sesi berikutnya tidak salah routing.

## Bahasa & nada

Ikuti tabel routing entitas di Langkah 0. Struktur PATO dan prinsip 4C tetap sama lintas bahasa, hanya bahasanya yang berubah. Untuk dokumen Indonesia, default formal-friendly dengan "Anda".

**Aturan harness: dilarang memakai em-dash.** Gunakan tanda hubung biasa.
