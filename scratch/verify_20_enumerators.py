import os

ktp_dir = "/mnt/c/Users/rifra/Downloads/KTP Enum Mutiara"
kk_dir = "/mnt/c/Users/rifra/Downloads/KK Enum Mutiara"

# Master list of 20 Enumerators
enumerators_20 = [
    ("Arif Rahman", "arif_rahman_ktp", "arif_rahman_kk"),
    ("Asep Hilmansyah", "asep_hilmansyah_ktp", "asep_hilmansyah_kk"),
    ("Duta Aditya", "duta_aditya_ktp", "duta_aditya_kk"),
    ("Fadhilah Kurniawan", "fadhilah_kurniawan_ktp", "fadhilah_kurniawan_kk"),
    ("Fadillah Nurachman", "fadillah_nurachman_ktp", "fadillah_nurachman_kk"),
    ("Fairuz Al Fajri", "fairuz_al_fajri_ktp", "fairuz_al_fajri_kk"),
    ("Febi Setiawan", "febi_setiawan_ktp", "febi_setiawan_kk"),
    ("M Taufik Akbar J", "m_taufik_akbar_j_ktp", "m_taufik_akbar_j_kk"),
    ("Mahendra Sadepi", "mahendra_sadepi_ktp", "mahendra_sadepi_kk"),
    ("Mamat Sofyan", "mamat_sofyan_ktp", "mamat_sofyan_kk"),
    ("Nanda Tryas Wicaksana", "nanda_tryas_wicaksana_ktp", "nanda_tryas_wicaksana_kk"),
    ("Nur Fadilla", "nur_fadilla_ktp", "nur_fadilla_kk"),
    ("Pitra", "pitra_ktp", "pitra_kk"),
    ("Rahmadi Atma Tristya", "rahmadi_atma_tristya_ktp", "rahmadi_atma_tristya_kk"),
    ("Rodiansyah", "rodiansyah_ktp", "rodiansyah_kk"),
    ("Ruly Hendro S", "ruly_hendro_s_ktp", "ruly_hendro_s_kk"),
    ("Tony Rayvaldo", "tony_rayvaldo_ktp", "tony_rayvaldo_kk"),
    ("Widi Setiawan", "widi_setiawan_ktp", "widi_setiawan_kk"),
    ("Yuda Adi Pradana", "yuda_adi_pradana_ktp", "yuda_adi_pradana_kk"),
    ("Yusri Fadlan", "yusri_fadlan_ktp", "yusri_fadlan_kk")
]

ktp_files = os.listdir(ktp_dir)
kk_files = os.listdir(kk_dir)

def find_file(directory_files, prefix):
    for f in directory_files:
        name_part = os.path.splitext(f)[0]
        if name_part == prefix or name_part.startswith(prefix):
            return f
    return None

print(f"{'No.':<4} {'Nama Enumerator':<25} {'File KTP':<30} {'File KK':<30} {'Status':<15}")
print("="*105)

complete_count = 0
incomplete_count = 0

for idx, (name, ktp_prefix, kk_prefix) in enumerate(enumerators_20, 1):
    ktp_found = find_file(ktp_files, ktp_prefix)
    kk_found = find_file(kk_files, kk_prefix)
    
    if ktp_found and kk_found:
        status = "✅ LENGKAP"
        complete_count += 1
    elif ktp_found and not kk_found:
        status = "⚠️ KURANG KK"
        incomplete_count += 1
    elif not ktp_found and kk_found:
        status = "⚠️ KURANG KTP"
        incomplete_count += 1
    else:
        status = "❌ HILANG KEDUA-DUANYA"
        incomplete_count += 1

    ktp_str = ktp_found if ktp_found else "-"
    kk_str = kk_found if kk_found else "-"
    print(f"{idx:<4} {name:<25} {ktp_str:<30} {kk_str:<30} {status:<15}")

print("="*105)
print(f"TOTAL DAFTAR ENUMERATOR : {len(enumerators_20)} Orang")
print(f"LENGKAP (KTP + KK)     : {complete_count} Orang")
print(f"BELUM LENGKAP          : {incomplete_count} Orang")
