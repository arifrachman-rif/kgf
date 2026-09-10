---
name: pitch-framework-3s
description: "PINTU MASUK untuk menjalankan pitch end-to-end pakai Framework 3S (Story-Slide-Simulate), atau untuk tahu 'saya di tahap mana'. Trigger: 'jalankan Framework 3S', 'bantu saya pitching dari nol', 'siapin pitch lengkap untuk [investor/klien/buyer/donor]', 'buatkan company profile', 'dari cerita sampai prototype', 'lanjutkan 3S saya', 'status pitch saya sampai mana', atau saat the owner mendeskripsikan bisnis dan minta disiapkan materi pitching menyeluruh tanpa menyebut tahap. JANGAN gunakan kalau the owner eksplisit minta satu tahap saja (pakai pitch-story / pitch-deck-builder / prototype-simulator langsung). Skill ini MENGORKESTRASI alur lintas tahap dan menegakkan urutan Story-Slide-Simulate, bukan mengulang isi kerja tiap tahap."
---

# Framework 3S - Orkestrator Story, Slide, Simulate

Pintu masuk Framework 3S. Tugasnya tiga: memastikan setiap pitch melewati urutan yang benar (narasi dulu, baru slide, baru prototype), menjaga handoff antar tahap tetap utuh (terutama tag `[BUKTI BELUM ADA]` yang tidak boleh hilang atau diam-diam diisi), dan menegakkan routing entitas supaya bahasa dan konteks tidak tertukar.

Skill ini mengorkestrasi dan menaikkan disiplin skill lain. Ia tidak menulis narasi, slide, atau prototype sendiri.

## Dasar metodologi

Urutan 3S bukan preferensi gaya. Empat prinsip yang mendasarinya:

- **Cognitive Load Theory** - audiens punya kapasitas kerja terbatas. Satu slide, satu beban.
- **Dual Coding** - kata plus visual diproses di dua kanal berbeda, retensinya lebih tinggi daripada salah satunya saja.
- **Assertion-Evidence** - headline slide adalah klaim yang bisa diperdebatkan, bukan label topik. Isinya adalah bukti pendukung klaim itu.
- **Picture Superiority Effect** - gambar lebih mudah diingat daripada teks setara.

Kalau ada dorongan untuk melompat langsung ke slide, ingat: narasi yang lemah membuat slide secantik apapun tidak menggerakkan.

## Skill di bawahnya

- Menyusun narasi: `pitch-story`
- Membangun deck (.pptx atau HTML on-brand): `pitch-deck-builder`
- Membangun demo interaktif: `prototype-simulator`
- Standar visual dan brand DNA: `power-design`

## Peta alur

```
        ide / deskripsi bisnis atau produk
                    |
                    v
   +------------------------------+
   |  S1 - STORY (pitch-story)    |  narasi PATO + tag [BUKTI BELUM ADA]
   +--------------+---------------+
                  v
      GERBANG 1: entitas & bahasa terkunci?
                  heading blok utuh?
                  tag bukti tidak hilang?
                  v
   +------------------------------+
   |  S2 - SLIDE                  |  deck dari blok narasi
   |  (pitch-deck-builder)        |
   +--------------+---------------+
                  v
      GERBANG 2: tidak ada angka karangan
                  menggantikan tag bukti?
                  v
   +------------------------------+
   |  S3 - SIMULATE               |  prototype interaktif
   |  (prototype-simulator)       |  (opsional, hanya jika ada demo produk)
   +--------------+---------------+
                  v
      GERBANG 3: alur klik teruji?
                  tampil baik di mobile?
                  v
          materi pitch siap dipakai
```

## Tahap 0 - Kunci entitas dulu

Sebelum apa pun, tentukan entitas mana. Ini mengubah bahasa dan isi secara total. Lihat tabel routing di `pitch-story`.

**BATAS KERAS dari CLAUDE.md:** KGF dan Pevesindo tidak punya kegiatan yang saling berkaitan. Jangan pernah mencampur konteks, data, atau klaim keduanya dalam satu dokumen kecuali the owner eksplisit memintanya.

Kalau the owner ingin materi untuk beberapa entitas, jalankan 3S **satu entitas per satu putaran**. Jangan bikin satu deck gabungan.

## Tahap 1 - Story

Panggil `pitch-story`. Jangan lewati meski the owner langsung minta "buatkan slide-nya" dari ide mentah. Tawarkan dulu susun narasi, kecuali the owner eksplisit menolak dan sudah punya struktur argumen sendiri. Dalam kasus itu, catat sebagai S1 "dilewati atas permintaan", bukan "belum dikerjakan".

**Gerbang sebelum lanjut:** entitas dan bahasa tercatat di kepala dokumen, heading blok (Problem/Agitate/Transformation/dst) utuh dan tidak diringkas, setiap `[BUKTI BELUM ADA]` masih bertag persis. Kalau the owner membawa narasi lama dari sesi lain yang formatnya sudah berubah, jangan asumsikan datanya lengkap. Konfirmasi dulu.

## Tahap 2 - Slide

Panggil `pitch-deck-builder` dengan narasi dari Tahap 1. Kalau masih ada `[BUKTI BELUM ADA]` yang terbuka, ikuti instruksi di skill tersebut: tanya the owner, jangan isi sendiri.

**Gerbang sebelum dianggap selesai:** baca ulang deck dan pastikan tidak ada angka yang muncul menggantikan tag bukti tanpa konfirmasi. Ini kegagalan paling mahal di seluruh alur, karena deck KGF dan aGROWforests bisa sampai ke auditor donor atau tim compliance buyer EU.

## Tahap 3 - Simulate (opsional)

Hanya relevan kalau pitch melibatkan demo produk yang bisa divisualisasikan sebagai alur klik (misalnya TAPAK). Tanyakan apakah tahap ini dibutuhkan. Jangan otomatis bangun prototype untuk pitch yang murni jasa, komoditas, atau kelembagaan tanpa antarmuka produk.

**Gerbang sebelum diserahkan:** alur klik diuji end-to-end, tampilan mobile dicek.

## State tracking

Untuk pitch yang berjalan lintas sesi, jaga status board ini dan tampilkan dulu kalau the owner bertanya "sudah sampai mana" atau kembali setelah jeda:

```markdown
## Framework 3S - Status: [Entitas / Nama Pitch]
Entitas: ... | Bahasa: ... | Audiens: ... | Satu ask: ...

| Tahap | Status | Catatan |
|-------|--------|---------|
| S1 Story | ok / jalan / belum / dilewati | tag [BUKTI BELUM ADA] tersisa: ... |
| S2 Slide | | jalur: pptx / HTML |
| S3 Simulate | ok / jalan / belum / tidak relevan | |
```

## Guardrail

1. **Urutan tidak boleh dibalik** tanpa alasan eksplisit dari the owner.
2. **Tag `[BUKTI BELUM ADA]` adalah sinyal, bukan gangguan.** Jangan pernah menghilangkannya diam-diam demi output yang terlihat lebih lengkap.
3. **S3 tidak default-on.** Banyak pitch (komoditas, jasa, kelembagaan, donor) tidak butuh prototype. Memaksakannya hanya menambah kerja tanpa nilai.
4. **Satu entitas per putaran.** Jangan menggabung KGF dengan Pevesindo.
5. **Dilarang em-dash** (aturan harness).

## Prinsip

- **Orchestrator ini tidak menulis konten.** Kalau tergoda menyusun narasi atau slide langsung di sini, berhenti dan panggil skill yang sesuai.
- **Handoff yang utuh lebih penting dari kecepatan.** Satu tag bukti yang hilang di tengah jalan berujung slide dengan klaim karangan di tahap berikutnya.
- **Kejujuran tentang kelengkapan materi.** Status board harus menampilkan gap apa adanya, bukan cuma progres yang terlihat baik.
