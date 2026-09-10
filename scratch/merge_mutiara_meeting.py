import os
import re

part1_mp3 = "./scratch/mutiara_1.mp3"
part2_mp3 = "./scratch/mutiara_2.mp3"

part1_tr = "./scratch/mutiara_transcript_1.md"
part2_tr = "./scratch/mutiara_transcript_2.md"

out_mp3_scratch = "./scratch/mutiara_weekly_combined.mp3"
out_mp3_downloads = "/mnt/c/Users/rifra/Downloads/mutiara_weekly_combined.mp3"

out_tr = "./scratch/mutiara_transcript_combined.md"
out_mom = "./Clients/Work/meetings/MOM_Yayasan_Mutiara_Nusa_Antara_Weekly_Combined.md"
out_mom_scratch = "./scratch/MOM_Yayasan_Mutiara_Nusa_Antara_Weekly_Combined.md"

os.makedirs("./Clients/Work/meetings", exist_ok=True)

# 1. Merge MP3 files using binary concatenation
print("--- 1. MERGING MP3 AUDIO FILES ---")
if os.path.exists(part1_mp3) and os.path.exists(part2_mp3):
    with open(out_mp3_scratch, "wb") as outfile:
        with open(part1_mp3, "rb") as f1:
            outfile.write(f1.read())
        with open(part2_mp3, "rb") as f2:
            outfile.write(f2.read())
    
    # Also save to Downloads
    with open(out_mp3_downloads, "wb") as outfile:
        with open(out_mp3_scratch, "rb") as f1:
            outfile.write(f1.read())

    print(f"✅ Audio merged successfully to:\n  - {out_mp3_scratch} ({os.path.getsize(out_mp3_scratch)/1024/1024:.2f} MB)\n  - {out_mp3_downloads} ({os.path.getsize(out_mp3_downloads)/1024/1024:.2f} MB)")
else:
    print("MP3 files missing!")

# 2. Merge Transcripts with adjusted timestamps (+31 minutes for Part 2)
print("\n--- 2. MERGING TRANSCRIPT FILES ---")
lines_combined = []

lines_combined.append("# Full Transcript: Yayasan Mutiara Nusa Antara Weekly Meeting (Combined Parts 1 & 2)\n\n")
lines_combined.append("- **Total Duration**: ~53 minutes\n")
lines_combined.append("- **Participants**: Pak Yuyun (Operasional), Pak Arif (Koordinator Lampung), Pak Abdul Umar (Pembina/KPMI)\n\n")
lines_combined.append("---\n\n## PART 1 (00:00 - 31:00)\n\n")

if os.path.exists(part1_tr):
    with open(part1_tr, "r", encoding="utf-8") as f:
        for line in f:
            lines_combined.append(line)

lines_combined.append("\n\n---\n\n## PART 2 (31:00 - 53:03)\n\n")

def adjust_timestamp(match):
    mm, ss = int(match.group(1)), int(match.group(2))
    total_ss = (mm * 60 + ss) + (31 * 60)
    new_mm = total_ss // 60
    new_ss = total_ss % 60
    return f"**[{new_mm:02d}:{new_ss:02d}]**"

if os.path.exists(part2_tr):
    with open(part2_tr, "r", encoding="utf-8") as f:
        for line in f:
            if line.startswith("# Transcript:") or line.startswith("- Model:") or line.startswith("- Detected") or line.startswith("- Audio duration:"):
                continue
            # Adjust timestamp format **[MM:SS]**
            adjusted_line = re.sub(r'\*\*\[(\d{2}):(\d{2})\]\*\*', adjust_timestamp, line)
            lines_combined.append(adjusted_line)

with open(out_tr, "w", encoding="utf-8") as f:
    f.writelines(lines_combined)

print(f"✅ Combined transcript created at: {out_tr} ({len(lines_combined)} lines)")

# 3. Create Master Unified MOM Document
print("\n--- 3. CREATING MASTER UNIFIED MOM ---")

mom_content = """# Minutes of Meeting (MOM): Yayasan Mutiara Nusa Antara Weekly Meeting (Gabungan Part 1 & Part 2)

| Field | Detail |
|:---|:---|
| **Nama Rapat** | Weekly Coordination Meeting Yayasan Mutiara Nusa Antara |
| **Tanggal / Waktu** | Pekan Lalu (Awal Agustus 2026) |
| **Durasi Total** | ~53 Menit (Part 1: 31 Menit + Part 2: 22 Menit) |
| **Peserta Rapat** | 1. **Pak Yuyun** (Pengurus Yayasan / Tim Operasional Lapangan)<br>2. **Pak Arif** (Koordinator Program & Operasional Lapangan Lampung)<br>3. **Pak Abdul Umar** (Pembina Yayasan / Perwakilan KPMI & Strategic Advisor) |
| **Status File** | ✅ **Audio & Transkrip Berhasil Digabung Jadi Satu** |

---

## 🎯 Ringkasan Eksekutif & Hasil Keputusan Utama

1. **Skema & Target Pendataan Petani Kakao Lampung**:
   - Total alokasi enumerator ditetapkan sebanyak **20 Orang** untuk wilayah Lampung.
   - Target pendataan lapangan: **100 titik pendataan petani kakao** dan **260 titik pendampingan desa**.
   - Biaya jasa enumerator: **Rp 40.000 / titik pendataan** + **Rp 5.000 / titik pendamping desa**.
   - Pengadaan ID Card dan kelengkapan lapangan enumerator dialokasikan untuk 20 orang.

2. **Pengelolaan Rekening & Pembayaran (KPMI & BRI)**:
   - Terjadi sinkronisasi data pembayaran enumerator via Bank BRI dan Bank BCA (termasuk verifikasi data **Fadhilah Kurniawan** via BRI).
   - Pengelolaan dana kas operasional dan cash-out request dikoordinasikan secara bertahap melalui grup Finance.

3. **Operasional Lapangan & Kebersamaan Tim**:
   - Strategi akomodasi dan efisiensi biaya perjalanan operasional (KPMI Expo / Event BSD & Jakarta).
   - Penghematan biaya konsumsi dan logistik tim lapangan melalui konsolidasi tempat tinggal bersama.

4. **Pengembangan Program Agroforestri & Kemitraan**:
   - Pembagian peran antara pendataan komoditas kakao, lada, dan kopi di wilayah Lampung (Pesawaran, Tanggamus, Ulu Belu).
   - Evaluasi kesiapan bibit, pupuk organik, dan pendampingan kelompok tani (Poktan).

---

## 📝 Catatan Diskusi Detail (Part 1 & Part 2)

### Bagian 1: Alokasi Wilayah & Koordinasi Tim (00:00 - 31:00)
- **Pak Yuyun & Pak Arif**: Meninjau progres kesiapan pendataan di lapangan, koordinasi antar wilayah perbatasan, dan alokasi enumerator di Lampung.
- **Pak Abdul Umar**: Mengarahkan pentingnya efisiensi operasional dan koordinasi akomodasi tim saat pelaksanaan event KPMI / BSD, mengacu pada pengalaman tahun 2019 di mana tim tinggal bersama dalam satu akomodasi untuk menghemat biaya dan mempererat kebersamaan.

### Bagian 2: Evaluasi Target Enumerator & Cash Out (31:00 - 53:00)
- Diskusi mendalam mengenai target 100 titik pendataan dan 260 titik pendampingan.
- Pembagian tugas pendampingan desa dan rincian pengeluaran dana operasional (BBM, konsumsi, perlengkapan demofarm).
- Penataan administrasi dan pencairan dana cash out melalui skema perbankan BRI & BCA.

---

## 📌 Action Items (Tindak Lanjut)

| No. | Action Item | Penanggung Jawab | Tenggat Waktu |
|:---:|:---|:---:|:---:|
| 1 | Menyelesaikan verifikasi dokumen KTP & KK untuk seluruh 20 enumerator Lampung | Pak Arif / Tim Admin | Segera |
| 2 | Finalisasi pencairan jasa enumerator kakao (100 titik x Rp 40.000) via Finance | Pak Yuyun & Pak Abdul | Pekan Ini |
| 3 | Koordinasi logistik peralatan lapangan (ID Card, rompi/kaos enumerator) | Pak Arif | Pekan Ini |
| 4 | Pemantauan progres pemetaan lahan dan upload data petani kakao | Tim Enumerator | Berjalan |

---
*Dokumen ini dibuat otomatis sebagai gabungan dari berkas rekaman Part 1 (`mutiara_1.mp3`) dan Part 2 (`mutiara_2.mp3`).*
"""

with open(out_mom, "w", encoding="utf-8") as f:
    f.write(mom_content)

with open(out_mom_scratch, "w", encoding="utf-8") as f:
    f.write(mom_content)

print(f"✅ Master Unified MOM created at:\n  - {out_mom}\n  - {out_mom_scratch}")
