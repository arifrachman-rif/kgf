---
name: prototype-simulator
description: "Bangun prototype interaktif yang bisa diklik untuk mensimulasikan produk/aplikasi/layanan ke calon klien atau investor — tanpa perlu tim developer. Ini adalah Skill 3 (Simulate) dari Framework 3S (Story-Slide-Simulate), dipakai setelah narasi (pitch-story) dan slide (pitch-deck-builder) siap, atau berdiri sendiri kapan saja user butuh demo visual dari sebuah ide produk. WAJIB gunakan setiap kali user minta 'buat prototype', 'bikin mockup interaktif', 'simulasikan produk ini', 'demo yang bisa diklik', 'S3 Framework 3S', 'bikin app demo untuk pitching ke klien/investor', atau mendeskripsikan sebuah aplikasi/produk dan ingin memvisualisasikannya secara nyata. JANGAN gunakan untuk membangun aplikasi produksi sungguhan dengan backend/database nyata (ini murni simulasi front-end untuk keperluan presentasi) — dan jangan gunakan untuk pitch deck slide (pakai pitch-deck-builder)."
---

# Prototype Simulator — Skill 3 dari Framework 3S

Bangun **prototype interaktif** — sebuah simulasi produk yang terlihat dan terasa nyata saat diklik, tapi tidak butuh backend sungguhan. Tujuannya satu: membuat calon klien/investor bisa *merasakan* produk dalam beberapa menit, bukan cuma membayangkannya dari deskripsi teks atau gambar statis.

Baca dulu `/mnt/skills/public/frontend-design/SKILL.md` (atau versi user jika tersedia) untuk standar kualitas visual — prototype ini harus terlihat seperti produk asli yang sudah jadi, bukan wireframe kasar. Untuk kalibrasi kualitas kelas dunia, baca juga `references/awwwards-inspiration.md` — ringkasan pola dari pemenang/nominee Awwwards (Site of the Year & koleksi SaaS/product) yang relevan khusus untuk demo produk interaktif, bukan sekadar situs artistik.

## Prinsip inti: Simulasi, bukan aplikasi sungguhan

Bedanya penting untuk ditegaskan ke user di awal jika mereka terdengar mengharapkan produk produksi:
- **Data statis/mock**, bukan koneksi database nyata — cukup realistis untuk terasa hidup (nama, angka, isi yang masuk akal), tidak perlu backend.
- **Alur klik yang direncanakan** (scripted flow) — tombol dan interaksi yang relevan dengan cerita demo harus benar-benar berfungsi; elemen di luar alur cerita boleh dekoratif/non-fungsional selama tidak terlihat rusak saat diklik.
- **Satu file HTML mandiri** (atau React artifact) yang bisa dibuka di browser mana pun tanpa instalasi — supaya bisa langsung dikirim ke klien via link atau dibuka di laptop saat meeting.

## Langkah kerja

### 1. Tentukan alur cerita demo (scripted flow)

Sebelum membangun apa pun, tentukan **3-6 langkah** yang akan diklik audiens selama demo, mengikuti alur transformasi dari narasi pitch (kalau ada dari `pitch-story`): mulai dari kondisi "masalah" sampai "hasil yang diinginkan". Contoh pola umum:
1. Layar masuk / kondisi awal (masalah terlihat)
2. Aksi utama pengguna (fitur inti dipakai)
3. Hasil / output yang dihasilkan produk
4. Momen "aha" — bagian paling meyakinkan dari seluruh demo, buat ini terlihat paling menonjol

Setiap langkah = satu state/screen yang bisa diklik untuk lanjut ke langkah berikutnya.

### 2. Bangun sebagai state machine sederhana

Gunakan satu variabel state (React `useState`, atau JS biasa untuk HTML) untuk berpindah antar langkah alur cerita. Setiap tombol yang termasuk alur cerita mengubah state ke langkah berikutnya. Jangan bangun navigasi bebas kompleks — tujuannya linear dan meyakinkan, bukan aplikasi penuh dengan semua kemungkinan jalur.

### 3. Isi dengan data yang terasa nyata

- Gunakan nama, angka, dan skenario yang relevan dengan bisnis/industri user — bukan "Lorem Ipsum" atau "User 1".
- Kalau produk untuk industri spesifik (F&B, retail, pendidikan, dst.), sesuaikan istilah dan contoh datanya.
- Angka yang ditampilkan boleh ilustratif untuk demo, tapi jangan diklaim sebagai data nyata ke audiens — user yang mempresentasikan harus tahu ini simulasi, bukan laporan.

### 4. Kualitas visual tinggi, bukan wireframe

Prototype ini akan dilihat langsung oleh calon klien/investor — bukan dokumentasi internal. Terapkan standar dari `frontend-design`: tipografi yang disengaja, palet warna yang koheren dengan brand user (tanyakan kalau belum ada), micro-interaction halus (transisi antar state, hover state pada tombol), dan tidak ada elemen default/generic AI (jangan gradient ungu template, jangan font Inter polos tanpa alasan).

Sebelum dianggap selesai, cek balik ke 6 prinsip di `references/awwwards-inspiration.md`: produk ditunjukkan sejak layar pertama, alur terpandu (bukan navigasi bebas), data terasa nyata (bukan Lorem Ipsum/clip-art), motion punya fungsi naratif (bukan hiasan), kesederhanaan yang rapi mengalahkan banyak efek setengah jadi, dan CTA/hierarki tidak hilang di tengah animasi.

### 5. Tambahkan micro-polish yang membuatnya terasa "hidup"

- Transisi antar state dengan animasi halus (fade/slide), bukan berpindah instan.
- Loading state singkat (0.3-0.6 detik) di titik yang meniru "proses" nyata (misalnya setelah klik "Generate" atau "Submit") — ini justru menambah kredibilitas dibanding instan.
- Feedback visual jelas saat tombol diklik (state aktif, warna berubah, dsb).
- **Kontrol reset yang tidak mencolok** (ikon kecil di sudut, atau klik logo) untuk kembali ke state awal — demo sungguhan hampir selalu dijalankan lebih dari sekali (latihan, audiens kedua, koneksi ulang), dan presenter yang harus refresh halaman di depan klien kehilangan momentum.

### 6. Pastikan tampil baik di layar kecil

Prototype ini sering dibuka calon klien langsung dari HP di tengah percakapan (bukan cuma di laptop saat meeting formal). Uji breakpoint mobile (viewport ~375-430px): teks tidak terpotong, tombol tetap mudah diklik dengan jempol, dan alur cerita tetap bisa diikuti tanpa scroll horizontal.

## Estimasi durasi demo

Selaraskan jumlah langkah (3-6) dengan slot waktu presentasi: 3-4 langkah untuk demo cepat di sela pitch (~2-3 menit), 5-6 langkah kalau memang ada slot demo terpisah (~5-7 menit). Kalau user tidak sebutkan slot waktu, tanyakan singkat di awal — jumlah langkah yang salah pilih adalah alasan umum demo terasa buru-buru atau bertele-tele.

## Kapan pakai HTML vs React artifact

- **HTML mandiri** — pilihan default kalau prototype akan dikirim sebagai file/link ke klien di luar percakapan Claude (lebih portabel, bisa dibuka di device mana pun).
- **React artifact** — kalau demo akan langsung ditunjukkan dalam sesi/percakapan yang sama dan butuh state management lebih kompleks.

Ikuti aturan artifact standar: tidak ada `localStorage`/`sessionStorage` di React artifact — gunakan `useState` untuk simulasi data selama sesi berjalan.

## Sebelum diserahkan: uji alur sendiri

Jalankan seluruh alur cerita dari langkah 1 sampai "momen aha" secara mental/kode sebelum present_files — pastikan tidak ada tombol dalam scripted flow yang macet atau state yang nyangkut. Cek juga sekali lagi ke 6 prinsip di `references/awwwards-inspiration.md` plus breakpoint mobile di atas.

## Sertakan catatan demo (wajib, singkat)

Bersama file prototype, serahkan **catatan demo** ringkas di percakapan: satu kalimat pengantar per layar (apa yang perlu diucapkan presenter sebelum audiens mengklik), plus satu instruksi kunci — **serahkan kendali kepada audiens: biarkan mereka yang mengklik, bukan presenter** (IKEA Effect, Norton dkk. 2012: orang menilai lebih tinggi apa yang ikut mereka alami sendiri). Prototype terbaik gagal berdampak kalau presenter memonopoli mouse dan mengubahnya jadi tontonan.

## Level penyebaran: dari file ke tautan permanen

Selaraskan bentuk akhir dengan kebutuhan pitch — jangan otomatis berhenti di file:
1. **Artifact/HTML lokal** — cukup untuk demo dalam pertemuan terdekat.
2. **File HTML dikirim** — untuk satu klien tertentu via WA/email.
3. **Tautan permanen (deploy)** — kalau prototype akan dipakai berulang di proposal, tanda tangan email, atau dibagikan luas, tawarkan deploy ke Vercel (via integrasi Vercel bila tersedia di sesi) sehingga punya URL tetap. Tawarkan ini secara eksplisit kalau user menyebut "kirim ke banyak prospek", "taruh di proposal", atau alur pitch-nya berulang — jangan tunggu diminta.

## Setelah selesai

Simpan sebagai file (jika HTML mandiri) ke `/mnt/user-data/outputs/` dan serahkan lewat `present_files`, atau tampilkan langsung sebagai artifact jika dalam sesi yang sama. Ingatkan user: prototype ini adalah alat bantu cerita untuk pitching — kalau klien tertarik dan minta produk sungguhan, itu proyek pengembangan terpisah, bukan lanjutan otomatis dari file ini.
