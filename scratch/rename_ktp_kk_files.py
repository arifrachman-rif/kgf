import os

ktp_dir = "/mnt/c/Users/rifra/Downloads/KTP Enum Mutiara"
kk_dir = "/mnt/c/Users/rifra/Downloads/KK Enum Mutiara"

# Mapping for KTP files
ktp_rename_map = {
    "Arif Rahman.png": "arif_rahman_ktp.png",
    "Arif Rahman (Original).jpeg": "arif_rahman_original_ktp.jpeg",
    "Asep Hilmansyah.png": "asep_hilmansyah_ktp.png",
    "Duta Aditya.png": "duta_aditya_ktp.png",
    "Fadillah Nurachman.png": "fadillah_nurachman_ktp.png",
    "Fairuz Al Fajri.png": "fairuz_al_fajri_ktp.png",
    "Febi Setiawan.png": "febi_setiawan_ktp.png",
    "Mahendra Sadepi.png": "mahendra_sadepi_ktp.png",
    "Nanda Tryas Wicaksana.png": "nanda_tryas_wicaksana_ktp.png",
    "Nur Fadilla.png": "nur_fadilla_ktp.png",
    "Pitra.png": "pitra_ktp.png",
    "Rahmadi Atma Tristya.png": "rahmadi_atma_tristya_ktp.png",
    "Rodiansyah.png": "rodiansyah_ktp.png",
    "Tony Rayvaldo.png": "tony_rayvaldo_ktp.png",
    "Widi Setiawan.png": "widi_setiawan_ktp.png",
    "Yuda Adi Pradana.png": "yuda_adi_pradana_ktp.png",
    "Yusri Fadlan.png": "yusri_fadlan_ktp.png",
    "mamat_sofyan2.pdf": "mamat_sofyan_ktp.pdf"
}

# Mapping for KK files
kk_rename_map = {
    "KK Arif Rahman.pdf": "arif_rahman_kk.pdf",
    "KK Asep Hilmansyah.pdf": "asep_hilmansyah_kk.pdf",
    "KK Fadillah Nurachman.pdf": "fadillah_nurachman_kk.pdf",
    "KK M Taufik Akbar J.jpeg": "m_taufik_akbar_j_kk.jpeg",
    "KK Mahendra.jpeg": "mahendra_sadepi_kk.jpeg",
    "KK Mamat Sofyan.pdf": "mamat_sofyan_kk.pdf",
    "KK Nanda Tryas.jpeg": "nanda_tryas_wicaksana_kk.jpeg",
    "KK Nur.jpeg": "nur_fadilla_kk.jpeg",
    "KK Pitra.pdf": "pitra_kk.pdf",
    "KK Rahmadi.jpeg": "rahmadi_atma_tristya_kk.jpeg",
    "KK Rodiansyah.jpeg": "rodiansyah_kk.jpeg",
    "KK Ruly Hendro S.jpeg": "ruly_hendro_s_kk.jpeg",
    "KK Tony.jpeg": "tony_rayvaldo_kk.jpeg",
    "KK Widi Setiawan.jpeg": "widi_setiawan_kk.jpeg",
    "KK YudaAP.pdf": "yuda_adi_pradana_kk.pdf",
    "KK Yusri fadlan.jpeg": "yusri_fadlan_kk.jpeg",
    "KK fairuz Al Fajri.jpeg": "fairuz_al_fajri_kk.jpeg"
}

print("=== RENAMING KTP FILES ===")
for old_name, new_name in ktp_rename_map.items():
    old_path = os.path.join(ktp_dir, old_name)
    new_path = os.path.join(ktp_dir, new_name)
    if os.path.exists(old_path):
        os.rename(old_path, new_path)
        print(f"  {old_name} -> {new_name}")

print("\n=== RENAMING KK FILES ===")
for old_name, new_name in kk_rename_map.items():
    old_path = os.path.join(kk_dir, old_name)
    new_path = os.path.join(kk_dir, new_name)
    if os.path.exists(old_path):
        os.rename(old_path, new_path)
        print(f"  {old_name} -> {new_name}")

print("\n=== UPDATED KTP FOLDER ===")
for f in sorted(os.listdir(ktp_dir)):
    print(" -", f)

print("\n=== UPDATED KK FOLDER ===")
for f in sorted(os.listdir(kk_dir)):
    print(" -", f)
