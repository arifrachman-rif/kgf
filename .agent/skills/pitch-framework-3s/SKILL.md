---
name: pitch-framework-3s
description: "PINTU MASUK saat user ingin menjalankan pitch secara end-to-end pakai Framework 3S (Story-Slide-Simulate) tanpa menyebut tahap spesifik, atau ingin tahu 'saya di tahap mana'. Trigger pada: 'jalankan Framework 3S', 'bantu saya pitching dari nol', 'siapin pitch lengkap untuk [investor/klien]', 'dari cerita sampai prototype', 'saya mau pitching ke [nama], bantu dari awal', 'lanjutkan 3S saya', 'status pitch saya sampai mana', atau saat user mendeskripsikan bisnis/produk dan minta disiapkan materi pitching menyeluruh tanpa menyebut mau mulai dari narasi/slide/prototype. Juga trigger saat user sudah punya hasil dari satu-dua tahap (mis. sudah ada narasi dari sesi lain) dan minta dilanjutkan. JANGAN gunakan jika user secara eksplisit hanya minta satu tahap (pakai pitch-story/pitch-deck-builder/prototype-simulator langsung) — skill ini khusus MENGORKESTRASI alur lintas tahap dan menegakkan urutan Story→Slide→Simulate, bukan mengulang isi kerja tiap tahap."
---

# Framework 3S — Orkestrator Story → Slide → Simulate

Pintu masuk Framework 3S. Tugasnya tiga: memastikan setiap pitch melewati urutan yang benar (narasi dulu, baru slide, baru prototype — bukan sebaliknya), menjaga handoff antar tahap tetap utuh (terutama tag `[BUKTI BELUM ADA]` yang tidak boleh hilang atau diam-diam diisi), dan menegakkan pengecekan disclosure risk sebelum materi keluar ke calon klien/investor. Pola yang sama dengan `trace-2-0` dan `legal-orchestrator`: skill ini mengorkestrasi dan menaikkan disiplin skill lain, bukan menulis narasi/slide/prototype sendiri.

## Kapan skill ini TIDAK cukup sendirian

Orchestrator ini tidak menggantikan tiga skill di bawahnya — ia memanggil mereka pada waktu yang tepat:
- Menyusun narasi → tetap `pitch-story`
- Membangun file .pptx → tetap `pitch-deck-builder`
- Membangun demo interaktif → tetap `prototype-simulator`
- Mengecek risiko bocor metodologi → `secret-sauce-guard` (dipanggil di gerbang, lihat di bawah)

## Peta Alur

```
        ide/deskripsi bisnis atau produk
                    │
                    ▼
   ┌─────────────────────────────┐
   │  S1 — STORY (pitch-story)   │  narasi PATO + tag [BUKTI BELUM ADA]
   └───────────────┬─────────────┘
                    ▼
        ★ GERBANG: heading blok utuh?
          tag bukti tidak hilang?
                    ▼
   ┌─────────────────────────────┐
   │  S2 — SLIDE                 │  .pptx dari blok narasi
   │  (pitch-deck-builder)       │
   └───────────────┬─────────────┘
                    ▼
        ★ GERBANG: slide "Cara Kerja" bocor
          metodologi berbayar? → secret-sauce-guard
                    ▼
   ┌─────────────────────────────┐
   │  S3 — SIMULATE               │  prototype interaktif
   │  (prototype-simulator)       │  (opsional — hanya jika ada demo produk)
   └───────────────┬─────────────┘
                    ▼
        ★ GERBANG: alur klik teruji?
          tampil baik di mobile?
                    ▼
          materi pitch siap dipakai
```

## Tahap 1 — Story

Panggil `pitch-story`. Jangan lewati tahap ini meski user langsung minta "buatkan slide-nya" dari ide mentah — tawarkan dulu susun narasi, kecuali user secara eksplisit menolak dan sudah punya struktur argumen sendiri yang jelas (dalam kasus itu, catat sebagai S1 "dilewati atas permintaan user", bukan "belum dikerjakan").

**Gerbang sebelum lanjut ke S2:** heading blok (Problem/Agitate/Transformation/dst) utuh dan tidak diringkas, setiap `[BUKTI BELUM ADA]` masih bertag persis seperti aslinya. Kalau user membawa narasi lama dari sesi lain yang formatnya sudah berubah/tag-nya hilang, jangan asumsikan datanya sudah lengkap — konfirmasi dulu ke user.

## Tahap 2 — Slide

Panggil `pitch-deck-builder` dengan narasi dari Tahap 1. Kalau ada `[BUKTI BELUM ADA]` yang masih terbuka, ikuti instruksi di skill tersebut (tanya user, jangan isi sendiri).

**Gerbang outline:** pastikan `pitch-deck-builder` menjalankan langkah outline-dulu (tabel judul assertion + jenis visual per slide, disetujui user SEBELUM render). Kalau alur sampai di render tanpa outline yang disetujui, hentikan dan mundur satu langkah — merevisi outline murah, merevisi file mahal.

**Gerbang sebelum dianggap selesai:** jika deck ini menjelaskan metodologi berbayar Sam/ANABA sendiri (Framework 3S, TRACE-Q, PSME, dsb.) sebagai bagian "Cara Kerja", tawarkan menjalankan `secret-sauce-guard` terhadap draft sebelum finalisasi — terutama untuk pitch yang tujuannya menjual training/konsultasi tentang metodologi itu. Ini bukan langkah wajib otomatis (jangan jalankan tanpa izin), tapi WAJIB ditawarkan secara eksplisit di titik ini, bukan diasumsikan tidak perlu.

## Tahap 3 — Simulate (opsional)

Hanya relevan kalau pitch melibatkan demo produk yang bisa divisualisasikan sebagai alur klik. Tanyakan ke user apakah tahap ini dibutuhkan — jangan otomatis bangun prototype untuk pitch yang murni jasa/konsultasi tanpa antarmuka produk.

**Gerbang sebelum diserahkan:** alur klik sudah diuji end-to-end (lihat "Sebelum diserahkan: uji alur sendiri" di `prototype-simulator`), tampilan mobile dicek.

## State Tracking

Untuk pitch yang berjalan lintas sesi, jaga status board ini dan tampilkan dulu kalau user bertanya "sudah sampai mana" atau kembali setelah jeda:

```markdown
## Framework 3S — Status: [Nama Pitch/Klien]
| Tahap | Status | Catatan |
|-------|--------|---------|
| S1 Story | ✅/⏳/❌/dilewati | tag [BUKTI BELUM ADA] tersisa: ... |
| S2 Slide | | outline disetujui? Y/T · secret-sauce-guard ditawarkan? Y/T |
| S3 Simulate | ✅/⏳/❌/tidak relevan | |
```

## Setelah ketiga tahap selesai

Materi siap bukan berarti pitch siap. Tawarkan satu langkah lanjutan secara eksplisit (jangan dijalankan tanpa persetujuan): latihan penyampaian — simulasi tanya-jawab dari sudut pandang audiens target (investor skeptis / procurement korporat / atasan), memakai materi yang baru selesai sebagai bahan. Banyak pitch gagal bukan di materi, tapi di jawaban atas pertanyaan ketiga.

## Guardrail

1. **Urutan tidak boleh dibalik** tanpa alasan eksplisit dari user. Story → Slide → Simulate ada karena narasi yang lemah membuat slide secantik apapun tidak menggerakkan — lihat prinsip di `pitch-story`.
2. **Tag `[BUKTI BELUM ADA]` adalah sinyal, bukan gangguan.** Jangan pernah menghilangkannya secara diam-diam di tahap manapun demi output yang "terlihat lebih lengkap".
3. **Gerbang secret-sauce-guard di S2 wajib ditawarkan**, bukan wajib dijalankan — keputusan tetap di tangan user, tapi orchestrator tidak boleh melewati penawaran ini untuk pitch yang menjual metodologi sendiri.
4. **S3 tidak default-on.** Banyak pitch (jasa, konsultasi, B2B non-produk) tidak butuh prototype — memaksakan S3 di sini hanya menambah kerja tanpa nilai.

## Prinsip

- **Orchestrator ini tidak menulis konten.** Kalau tergoda menyusun narasi/slide/prototype langsung di sini, berhenti — panggil skill yang sesuai.
- **Handoff yang utuh lebih penting dari kecepatan.** Satu tag bukti yang hilang di tengah jalan bisa berujung slide dengan klaim karangan di tahap berikutnya.
- **Kejujuran tentang kelengkapan materi** — status board harus menampilkan gap apa adanya, bukan cuma progres yang terlihat baik.
