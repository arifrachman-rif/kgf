---
name: WhatsApp Connector
description: Read and send on WhatsApp Web over a persistent CDP browser session inside WSL. Find contacts, dump chat history, list and download document attachments, and send messages with target verification so a private message can never land in a group.
---

# WhatsApp Connector

Drives an already-logged-in WhatsApp Web session through Chrome DevTools
Protocol. Nothing here logs in or scans a QR code by itself.

## Where things actually live

| Bagian | Lokasi |
| :--- | :--- |
| Sesi login (profil Chrome, ~1 GB) | `~/.config/antigravity-chrome-data` **di dalam WSL Ubuntu** |
| Browser service | WSL, port `9222`, dijalankan dengan `xvfb-run` |
| Repo dilihat dari WSL | `/mnt/c/Users/<user>/.gemini/antigravity-ide/scratch/ai-second-brain` |

Ini **hanya jalan dari dalam WSL**. Tidak ada profil WhatsApp di sisi Windows,
dan `ensure_cdp.sh` memang skrip Linux (`xvfb-run`, path `chrome-linux`).

## Menyalakan browser service

Harus proses **persisten**. Menjalankannya dengan `&` di dalam
`wsl -- bash -lc "... &"` akan mati begitu perintah WSL selesai, dan gejalanya
membingungkan: CDP sempat hidup lalu hilang beberapa detik kemudian.

```bash
# di dalam WSL, tahan prosesnya (mis. sebagai background task yang tidak ditutup)
exec xvfb-run -a python3 .agent/skills/browser-service/scripts/playwright_cdp_server.py
```

Cek siap atau belum:

```bash
curl -s http://127.0.0.1:9222/json/version
python3 .agent/skills/whatsapp-connector/check_wa.py   # "WhatsApp is connected and ready."
```

Kalau muncul QR code, sesi kedaluwarsa dan pemilik harus memindai ulang sekali
lewat jendela Chrome yang terlihat.

## Perkakas: `wa_tools.py`

Semua dijalankan dari root repo, di dalam WSL.

```bash
S=.agent/skills/whatsapp-connector/wa_tools.py

# cari kontak, dan lihat apakah namanya cocok PERSIS
python3 $S find "Yuyun"

# tampilkan seluruh pesan yang termuat, dengan nomor baris
python3 $S dump "Hariyadi"

# daftar lampiran dokumen beserta nomor barisnya
python3 $S list-docs "Hariyadi"

# unduh lampiran berdasarkan nomor baris dari list-docs
python3 $S download "Hariyadi" --rows 35,37,38 --out ./wadocs

# kirim: TANPA --send hanya verifikasi target, tidak mengirim apa pun
python3 $S send "Yuyun Kurniawan" --file pesan.txt
python3 $S send "Yuyun Kurniawan" --file pesan.txt --send
```

`--file` dipakai untuk pesan multi-baris. Enter di WhatsApp berarti kirim, jadi
baris baru diketik sebagai Shift+Enter.

## Aturan pengiriman

**Selalu jalankan dry-run lebih dulu, dan tetap minta persetujuan pemilik
sebelum `--send`.** Approval gate di CLAUDE.md berlaku penuh untuk WhatsApp.

`send` membatalkan diri sendiri kalau:

- nama di header percakapan tidak **sama persis** dengan argumen `chat`, atau
- header memuat penanda grup (`participants`, `is also in this group`, dan
  sejenisnya).

Ini bukan kehati-hatian berlebihan. Mencari "Yuyun" memunculkan kontak lain
("Yuyun Keripik Asya") dan beberapa grup yang memuat teks
"Yuyun Kurniawan is also in this group" (aGROWforests Reborn, Mitra Kadin RFBH).
Tanpa verifikasi, pesan personal bisa tersiar ke grup, dan itu tidak bisa
ditarik kembali.

## `wa_manager.py` (lama)

Masih ada karena punya jalur kirim lampiran berkas yang belum dipindahkan ke
`wa_tools.py`. **Jangan pakai untuk mengirim teks**: ia memilih chat dengan
`get_by_title(name).first` tanpa verifikasi apa pun, sehingga bisa nyasar ke
grup seperti dijelaskan di atas.

```bash
# hanya untuk melampirkan berkas, dan pastikan nama kontaknya persis
python3 .agent/skills/whatsapp-connector/wa_manager.py send \
  --to "Nama Persis" --message "..." --file /path/berkas.pdf
```

## Catatan selector (hasil coba-coba, jangan diubah tanpa alasan)

- Kotak pencarian dan kotak ketik ada di balik shadow root Lexical milik Meta.
  Selector CSS meleset; `get_by_role("textbox")` menembusnya.
- Scroll dengan mouse wheel **tidak** memicu pemuatan riwayat. Kontainer scroll
  yang sebenarnya harus dicari lalu digerakkan lewat `scrollTop`.
- Bubble dokumen hanya punya afordans `title="View ..."`. Tombol unduhnya ada di
  **viewer layar penuh**, sebagai `button[aria-label="Download"]`.
- Viewer yang tertinggal terbuka dari pemanggilan sebelumnya akan menelan semua
  klik berikutnya. Setiap perintah menutupnya lebih dulu.
- `[title]` pertama di header chat adalah tombol "Profile details", bukan nama
  kontak. Nama chat adalah baris pertama `innerText` header.
- Deteksi dokumen tidak boleh hanya mengandalkan ekstensi berkas. WhatsApp
  kadang menampilkan nama tanpa ekstensi (mis. `DOC-20260225-WA0016.`), jadi
  baris metadata ("40 pages - PDF - 2 MB") dan ikon dokumen ikut diperiksa.

---

## Upstream Alternative: macOS Go Bridge (`whatsapp-mcp`)

*(Catatan: Bagian di bawah ini adalah konfigurasi upstream untuk macOS launchd Go bridge. Untuk lingkungan Windows/WSL, gunakan metode browser-service CDP di atas).*

This is personal infrastructure, not Work client work. It runs outside this repo's client connectors and outside the ASB app.

## How it's wired on this machine

- **Bridge**: a local Go process, `com.owner.wa-bridge`, managed by launchd,
  serving REST on `localhost:8080`.
- **MCP server**: `~/wa-bridge/whatsapp-mcp-server`, run via `uv`, talking
  to the bridge over stdio.
- **Credentials**: the WhatsApp account session lives under `~/wa-bridge/store/`
  and never leaves this machine.

## Send mode

`WA_SEND_MODE` gates every send tool. Default on this machine is
**disabled** (read-only): send tools refuse outright. In **approval** mode,
a send tool does not deliver anything. It appends the draft to
`~/.local/share/whatsapp-mcp/outbox.jsonl` and returns "staged", and the owner
approves it out-of-band with `approve.py`, separate from this chat.

