# Referensi Awwwards — Standar Kualitas Prototyping

Kumpulan referensi situs pemenang/nominee Awwwards yang relevan untuk membangun prototype produk interaktif berkualitas tinggi — bukan sekadar wireframe atau mockup generik. Dipakai sebagai kalibrasi kualitas visual sebelum menyerahkan prototype ke user, khususnya untuk demo yang akan ditunjukkan ke klien/investor.

Awwwards (awwwards.com) adalah lembaga penghargaan desain web asal Spanyol sejak 2009, menilai submission dari juri profesional atas kreativitas, kemampuan teknis, dan kualitas interaksi. Kategori tertinggi mereka adalah **Site of the Day → Site of the Month → Site of the Year**.

## Pemenang Site of the Year (acuan kualitas tertinggi)

| Tahun | Situs | Catatan relevansi |
|---|---|---|
| 2025 | Igloo Inc | Business & services — storytelling produk lewat motion halus |
| 2024 | Don't Board Me | Interaksi playful, transisi state yang terasa hidup |
| 2024 | Opal Tadpole | Agency automation product — demo produk terpandu (guided product demo) |
| 2024 | Lusion v3 | Studio kreatif — showcase teknis 3D/WebGL kelas dunia |
| 2023 | Noomo Agency | Palet warna tenang, efek 3D halus, mudah dipahami — **kesederhanaan yang tetap terasa premium** |
| 2023 | Mana Yerba Mate | Storytelling berbasis scroll |
| 2023 | KPR | Craft & tipografi kuat |
| 2022 | The Other Side of Truth | Narasi interaktif emosional |
| 2022 | Persepolis Reimagined | Data + budaya, interaksi berlapis |

## Situs produk/SaaS relevan untuk simulasi produk

Paling relevan untuk `prototype-simulator` karena ini bukan situs artistik, tapi **situs yang tugasnya sama seperti skill ini: membuat orang percaya pada sebuah produk dalam hitungan detik**.

- **Opal (Site of the Year 2024, kategori automation/agency tool)** — guided storytelling, demo produk animasi, blok teks-visual bergantian yang menyorot fitur kunci satu per satu.
- **Huly** (project management/collaboration tool) — dark interface + blok warna cerah, motion-based storytelling, transisi antar state terasa fluid, bukan potongan-potongan.
- **Clay** (AI CRM) — tipografi tebal berani, demo produk langsung ("straightforward product demos"), ilustrasi minimal — informasi didahulukan di atas dekorasi.
- **Flotorch** — dark theme kontemporer + gradient, hierarki visual & CTA jelas, demo produk interaktif eksplisit untuk membangun kepercayaan.
- **Kriss.ai, Watson, Zentry** (Awwwards Site of the Month 2024) — contoh situs produk AI dengan demo terintegrasi ke narasi halaman, bukan ditempel terpisah.

## Prinsip yang bisa langsung diterapkan ke prototype

Diringkas dari pola berulang di situs-situs pemenang di atas, plus temuan riset industri soal SaaS/product websites 2025-2026 — jadikan checklist sebelum menyerahkan prototype:

1. **Tunjukkan produk di atas layar pertama (above the fold), bukan janji abstrak.** Pemenang-pemenang di atas langsung memperlihatkan interface/output produk dalam beberapa detik pertama — audiens tidak perlu scroll jauh untuk mengerti apa yang ditawarkan. Terapkan: state pertama dalam alur cerita `prototype-simulator` harus langsung menunjukkan sesuatu yang konkret, bukan halaman "selamat datang" kosong.

2. **Demo terpandu (guided), bukan eksplorasi bebas.** Opal dan Clay membangun narasi step-by-step yang menyorot satu fitur dalam satu waktu. Ini sejalan dengan prinsip "scripted flow" di skill ini — jangan bangun navigasi bebas yang membingungkan, arahkan audiens lewat urutan yang sudah direncanakan.

3. **Interface nyata, bukan ilustrasi generik.** Riset SaaS 2026 menegaskan: situs yang menang adalah yang menunjukkan UI asli/mendekati asli, bukan ilustrasi dekoratif tentang "orang-orang bekerja sama". Terapkan: mock data harus terlihat seperti data produk sungguhan (nama, angka, tabel, dashboard nyata), bukan clip-art.

4. **Motion sebagai penjelasan, bukan hiasan.** Transisi di Huly dan situs sejenis menjelaskan hubungan sebab-akibat (klik ini → hasil itu muncul), bukan animasi dekoratif tanpa makna. Setiap animasi di prototype harus punya fungsi naratif.

5. **Kesederhanaan yang tetap premium (lihat Noomo Agency).** Warna tenang + satu efek 3D/motion yang dieksekusi rapi mengalahkan banyak efek yang dieksekusi setengah-setengah. Kalau ragu antara menambah satu elemen mewah lagi atau merapikan yang sudah ada, pilih merapikan.

6. **CTA & hierarki visual tetap jelas walau interaktif.** Flotorch dinilai kuat karena CTA & hierarki visual tidak "hilang" di tengah animasi. Prototype yang dibangun skill ini tetap harus punya titik akhir yang jelas (momen "aha" di alur cerita), bukan cuma pameran interaksi tanpa arah.

## Cara pakai referensi ini

Sebelum finalisasi prototype, cek balik terhadap 6 prinsip di atas seperti checklist singkat. Referensi ini BUKAN untuk ditiru persis (banyak situs Awwwards pakai WebGL/Three.js kompleks yang di luar cakupan single-file HTML/React artifact) — tapi untuk mengambil **prinsip di baliknya**: produk ditunjukkan lebih dulu, alur terpandu, data terasa nyata, motion bermakna, kesederhanaan yang rapi, dan CTA yang tidak hilang di tengah kemewahan visual.
