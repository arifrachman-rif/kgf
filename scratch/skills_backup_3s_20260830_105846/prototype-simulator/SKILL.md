---
name: prototype-simulator
description: "Bangun prototype interaktif yang bisa diklik untuk mensimulasikan produk/aplikasi/layanan ke calon klien, buyer, atau investor - tanpa tim developer. Skill 3 (Simulate) dari Framework 3S, dipakai setelah narasi (pitch-story) dan slide (pitch-deck-builder) siap, atau berdiri sendiri kapan saja butuh demo visual dari sebuah ide produk. Trigger: 'buat prototype', 'bikin mockup interaktif', 'simulasikan produk ini', 'demo yang bisa diklik', 'S3 Framework 3S', 'bikin app demo untuk pitching'. JANGAN gunakan untuk membangun aplikasi produksi dengan backend/database nyata (ini murni simulasi front-end untuk presentasi), dan jangan untuk pitch deck slide (pakai pitch-deck-builder)."
---

# Prototype Simulator - Skill 3 dari Framework 3S

Bangun **prototype interaktif**: simulasi produk yang terlihat dan terasa nyata saat diklik, tapi tidak butuh backend. Tujuannya satu, membuat calon klien atau buyer bisa *merasakan* produk dalam beberapa menit, bukan membayangkannya dari deskripsi teks.

Untuk standar kualitas visual, panggil skill `power-design` (deck dan web on-brand, dengan brand DNA di `.agent/skills/power-design/brands/`). Untuk kalibrasi kelas dunia, baca juga `references/awwwards-inspiration.md` di folder ini.

## Prinsip inti: simulasi, bukan aplikasi sungguhan

Tegaskan ke the owner di awal kalau terdengar mengharapkan produk produksi:

- **Data statis/mock**, bukan koneksi database nyata. Cukup realistis untuk terasa hidup (nama, angka, isi yang masuk akal).
- **Alur klik yang direncanakan** (scripted flow). Tombol yang relevan dengan cerita demo harus benar-benar berfungsi. Elemen di luar alur boleh dekoratif selama tidak terlihat rusak saat diklik.
- **Satu file HTML mandiri**, bisa dibuka di browser mana pun tanpa instalasi, supaya bisa langsung dikirim ke klien via link atau dibuka di laptop saat meeting.

## Langkah kerja

### 1. Tentukan alur cerita demo

Sebelum membangun apa pun, tentukan **3-6 langkah** yang akan diklik audiens, mengikuti alur transformasi dari narasi pitch (kalau ada dari `pitch-story`): dari kondisi "masalah" sampai "hasil yang diinginkan". Pola umum:

1. Layar masuk / kondisi awal (masalah terlihat)
2. Aksi utama pengguna (fitur inti dipakai)
3. Hasil / output yang dihasilkan produk
4. Momen "aha", bagian paling meyakinkan dari seluruh demo. Buat ini paling menonjol.

Setiap langkah = satu state yang bisa diklik untuk lanjut.

### 2. Bangun sebagai state machine sederhana

Satu variabel state untuk berpindah antar langkah. Setiap tombol dalam alur cerita mengubah state ke langkah berikutnya. Jangan bangun navigasi bebas yang kompleks. Tujuannya linear dan meyakinkan, bukan aplikasi penuh dengan semua kemungkinan jalur.

### 3. Isi dengan data yang terasa nyata

- Nama, angka, dan skenario yang relevan dengan bisnis atau industri terkait. Bukan "Lorem Ipsum" atau "User 1".
- Sesuaikan istilah dengan domainnya. Untuk TAPAK misalnya: nama petani, kode lahan, batch lada, koordinat plot, status verifikasi. Untuk Pevesindo: SKU plafon PVC, dimensi, stok gudang, status pengiriman.
- Angka boleh ilustratif untuk demo, tapi **jangan diklaim sebagai data nyata** ke audiens. The owner yang mempresentasikan harus tahu ini simulasi, bukan laporan. Kalau prototype akan ditunjukkan ke buyer atau auditor, beri label "illustrative data" yang terlihat.

### 4. Kualitas visual tinggi, bukan wireframe

Prototype ini dilihat langsung oleh calon klien atau buyer. Terapkan standar dari `power-design`: tipografi yang disengaja, palet koheren dengan brand entitas terkait (tanyakan kalau belum ada), micro-interaction halus. Hindari elemen default generik AI (gradient ungu template, font Inter polos tanpa alasan).

Sebelum dianggap selesai, cek balik ke 6 prinsip di `references/awwwards-inspiration.md`.

### 5. Micro-polish yang membuatnya terasa hidup

- Transisi antar state dengan animasi halus (fade/slide), bukan berpindah instan.
- Loading state singkat (0.3-0.6 detik) di titik yang meniru proses nyata (setelah klik "Generate" atau "Submit"). Ini justru menambah kredibilitas dibanding instan.
- Feedback visual jelas saat tombol diklik.

### 6. Pastikan tampil baik di layar kecil

Prototype sering dibuka calon klien langsung dari HP di tengah percakapan. Uji breakpoint mobile (viewport 375-430px): teks tidak terpotong, tombol mudah diklik dengan jempol, alur cerita tetap bisa diikuti tanpa scroll horizontal.

## Estimasi durasi demo

Selaraskan jumlah langkah dengan slot presentasi: 3-4 langkah untuk demo cepat di sela pitch (2-3 menit), 5-6 langkah kalau ada slot demo terpisah (5-7 menit). Kalau the owner tidak sebutkan slot waktu, tanyakan singkat. Jumlah langkah yang salah adalah alasan umum demo terasa buru-buru atau bertele-tele.

## HTML mandiri vs artifact

- **HTML mandiri** - default kalau prototype akan dikirim sebagai file atau link ke klien di luar percakapan. Lebih portabel.
- **Artifact** - kalau demo akan langsung ditunjukkan dalam sesi yang sama. Untuk artifact, muat dulu skill `artifact-design`, dan ingat semua aset harus inline (CSP memblokir host eksternal).

## Sebelum diserahkan: uji alur sendiri

Jalankan seluruh alur dari langkah 1 sampai momen "aha" sebelum menyerahkan. Pastikan tidak ada tombol dalam scripted flow yang macet atau state yang nyangkut. Cek juga 6 prinsip di `references/awwwards-inspiration.md` plus breakpoint mobile.

## Setelah selesai

Simpan file dan laporkan lokasinya. Ingatkan the owner: prototype ini alat bantu cerita untuk pitching. Kalau klien tertarik dan minta produk sungguhan, itu proyek pengembangan terpisah, bukan lanjutan otomatis dari file ini.
