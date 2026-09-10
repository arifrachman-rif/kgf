import os

ktp_dir = "/mnt/c/Users/rifra/Downloads/KTP Enum Mutiara"
kk_dir = "/mnt/c/Users/rifra/Downloads/KK Enum Mutiara"

ktp_files = os.listdir(ktp_dir)
kk_files = os.listdir(kk_dir)

# Master roster mapping canonical person name -> (ktp_filename, kk_filename)
# Let's map each person carefully:

people = [
    ("Arif Rahman", "Arif Rahman.png", "KK Arif Rahman.pdf"),
    ("Asep Hilmansyah", "Asep Hilmansyah.png", "KK Asep Hilmansyah.pdf"),
    ("Duta Aditya", "Duta Aditya.png", None),
    ("Fadillah Nurachman", "Fadillah Nurachman.png", "KK Fadillah Nurachman.pdf"),
    ("Fairuz Al Fajri", "Fairuz Al Fajri.png", "KK fairuz Al Fajri.jpeg"),
    ("Febi Setiawan", "Febi Setiawan.png", None),
    ("M Taufik Akbar J", None, "KK M Taufik Akbar J.jpeg"),
    ("Mahendra Sadepi", "Mahendra Sadepi.png", "KK Mahendra.jpeg"),
    ("Mamat Sofyan", "mamat_sofyan2.pdf", "KK Mamat Sofyan.pdf"),
    ("Nanda Tryas Wicaksana", "Nanda Tryas Wicaksana.png", "KK Nanda Tryas.jpeg"),
    ("Nur Fadilla", "Nur Fadilla.png", "KK Nur.jpeg"),
    ("Pitra", "Pitra.png", "KK Pitra.pdf"),
    ("Rahmadi Atma Tristya", "Rahmadi Atma Tristya.png", "KK Rahmadi.jpeg"),
    ("Rodiansyah", "Rodiansyah.png", "KK Rodiansyah.jpeg"),
    ("Ruly Hendro S", None, "KK Ruly Hendro S.jpeg"),
    ("Tony Rayvaldo", "Tony Rayvaldo.png", "KK Tony.jpeg"),
    ("Widi Setiawan", "Widi Setiawan.png", "KK Widi Setiawan.jpeg"),
    ("Yuda Adi Pradana", "Yuda Adi Pradana.png", "KK YudaAP.pdf"),
    ("Yusri Fadlan", "Yusri Fadlan.png", "KK Yusri fadlan.jpeg")
]

print(f"{'No.':<4} {'Nama Lengkap':<25} {'KTP':<30} {'KK':<30} {'Status':<15}")
print("="*105)

complete_count = 0
ktp_only_count = 0
kk_only_count = 0

for i, (name, ktp, kk) in enumerate(people, 1):
    has_ktp = ktp is not None and os.path.exists(os.path.join(ktp_dir, ktp))
    has_kk = kk is not None and os.path.exists(os.path.join(kk_dir, kk))
    
    status = ""
    if has_ktp and has_kk:
        status = "✅ LENGKAP"
        complete_count += 1
    elif has_ktp and not has_kk:
        status = "⚠️ HANYA KTP"
        ktp_only_count += 1
    elif not has_ktp and has_kk:
        status = "⚠️ HANYA KK"
        kk_only_count += 1
    else:
        status = "❌ TIDAK ADA"
        
    ktp_str = ktp if has_ktp else "-"
    kk_str = kk if has_kk else "-"
    print(f"{i:<4} {name:<25} {ktp_str:<30} {kk_str:<30} {status:<15}")

print("="*105)
print(f"Total Nama Terdeteksi: {len(people)}")
print(f"Lengkap KTP & KK    : {complete_count}")
print(f"Hanya Memiliki KTP  : {ktp_only_count}")
print(f"Hanya Memiliki KK   : {kk_only_count}")
