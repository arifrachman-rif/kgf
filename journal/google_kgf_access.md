# Google Access Map — arif@klumbayanfarm.com (KGF Work)

> Dibuat: 2026-08-22. Tujuan: supaya agent (Claude/Cline) selalu memakai identitas
> klumbayan dengan path token yang benar, dan tidak nyasar ke pevesindo.

## ⚠️ Akar masalah yang sudah terverifikasi (2026-08-22)

Di lingkungan Cline, env var global **`GMAIL_TOKEN_FILE` ter-set ke
`.agent\skills\gmail-connector\token_gmail_pevesindo.json`**.

Akibatnya: setiap panggilan `gmail_manager.py` **tanpa override eksplisit**
otomatis membaca token pevesindo → `User: arif@pevesindo.co.id`.
Inilah sebab Cline "hanya melihat pevesindo", padahal Claude menemukan email
klumbayan — Claude memakai shell tanpa env var itu (default token work).

**Aturan wajib (rule of thumb):**
1. Selalu sebut path token / profile secara EKSPLISIT. JANGAN pernah
   mengandalkan default Gmail.
2. Untuk Gmail, selalu override `GMAIL_TOKEN_FILE` di baris perintah yang sama.
3. Jangan buat OAuth flow/token baru — semua token sudah ada dan valid
   (refresh_token tersimpan; expiry lewat bukan berarti login ulang).
4. OAuth client satu-satunya: `.agent/skills/work-drive-connector/credentials.json`
   (GCP project ai-second-brain-504508, typed installed/Desktop).
   Gmail & Calendar meminjam file yang sama.

## Peta akun ↔ token path

| Identitas | Path token | Scope | Profile/flag |
|---|---|---|---|
| arif@klumbayanfarm.com (KGF Work) | `.agent/skills/work-drive-connector/token.json` | drive (full) | folder work-drive-connector |
| arif.rachman@gmail.com (personal) | `.agent/skills/personal-drive-connector/token.json` | drive | folder personal-drive-connector |
| arif@pevesindo.co.id (secondary) | `.agent/skills/secondary-drive-connector/token.json` | drive | folder secondary-drive-connector |
| Gmail klumbayan | `.agent/skills/gmail-connector/token_gmail_work.json` | gmail.modify | `GMAIL_TOKEN_FILE=` path tsb |
| Gmail pevesindo | `.agent/skills/gmail-connector/token_gmail_pevesindo.json` | gmail.modify | `GMAIL_TOKEN_FILE=` path tsb |
| Calendar klumbayan | `.agent/skills/work-drive-connector/token_calendar_work.json` | calendar.events + readonly | `--profile work` |
| Calendar secondary | `.agent/skills/secondary-drive-connector/token_calendar_secondary.json` | calendar.events + readonly | `--profile secondary` |

### Gmail — cara panggil (WAJIB override env)

```bash
# klumbayan (default yg benar)
GMAIL_TOKEN_FILE=.agent/skills/gmail-connector/token_gmail_work.json \
  python .agent/skills/gmail-connector/gmail_manager.py profile

# pevesindo (hanya jika memang mau ini)
GMAIL_TOKEN_FILE=.agent/skills/gmail-connector/token_gmail_pevesindo.json \
  python .agent/skills/gmail-connector/gmail_manager.py profile
```

Perintah lain: `list --query "..."`, `send --to ... --subject ... --body-file ...`.
Lihat `.agent/skills/gmail-connector/SKILL.md` untuk detail.

### Drive + Docs + Sheets — klumbayan

```bash
python .agent/skills/work-drive-connector/gdrive_manager.py search --query "NOTULENSI"
python .agent/skills/work-drive-connector/gdrive_manager.py read --id <FILE_ID>
# upload/convert juga didukung (--convert), set commenter otomatis
```

Scope drive penuh sudah diterima oleh Docs API & Sheets API — tidak perlu
scope documents/spreadsheets tambahan.

### Calendar — klumbayan

```bash
python .agent/skills/google-calendar-connector/gcal_manager.py list --profile work --days-back 14 --days-forward 14
```

## Status layanan (hasil verifikasi 2026-08-22, identitas klumbayan)

| Layanan | Status | Bukti |
|---|---|---|
| Gmail | ✅ OK | profile → arif@klumbayanfarm.com, 4.714 pesan |
| Drive | ✅ OK | search NOTULENSI → 1 file |
| Docs | ✅ OK | read "NOTULENSI 17 AGUSTUS 2026" (id `1rCswf8upJ2Fjg1A8ULr7yKEt01umu6bo64tf6uwY2D8`) |
| Sheets | ✅ OK | read "Improvement Plan for KGF" (id `1pIFqfrU7NjulprLHSV0XEgWj2pEz2ETDMdzwk1GpfLI`) |
| Calendar | ✅ OK | list 2026-08-08 s/d 2026-09-05 (Rapat KGF, aGROWforests, DSA, dll) |
| Slides | ⚠️ GAGAL 403 | Slides API belum aktif di project `388135103310` — bukan masalah scope/akun |

### Slides — solusi (sekali klik, hanya pemilik GCP bisa)

Aktifkan Google Slides API:
`https://console.developers.google.com/apis/api/slides.googleapis.com/overview?project=388135103310`

> Catatan: untuk sekadar *membaca/export* konten Slides, scope drive penuh
> sudah cukup via `gdrive_manager.py read --id <SLIDE_ID>` (export). 403 terjadi
> hanya pada panggilan `slides.googleapis.com` langsung (create/edit/present).

## Dokumen kunci klumbayan (hasil verifikasi)

- NOTULENSI 17 AGUSTUS 2026 (Docs): `1rCswf8upJ2Fjg1A8ULr7yKEt01umu6bo64tf6uwY2D8`
- Improvement Plan for KGF (Sheets): `1pIFqfrU7NjulprLHSV0XEgWj2pEz2ETDMdzwk1GpfLI`