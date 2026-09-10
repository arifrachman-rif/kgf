import wave
import os
import shutil

def trim_wav(input_path, output_path, max_duration_sec):
    try:
        print(f"Memproses {os.path.basename(input_path)}...")
        with wave.open(input_path, 'rb') as in_wav:
            params = in_wav.getparams()
            framerate = in_wav.getframerate()
            
            # Hitung jumlah maksimum frame yang diizinkan (Durasi x Framerate)
            max_frames = int(max_duration_sec * framerate)
            
            with wave.open(output_path, 'wb') as out_wav:
                out_wav.setparams(params)
                out_wav.setnframes(max_frames) # Paksa header untuk durasi baru
                
                # Baca dan tulis secara bertahap (chunking) untuk mencegah RAM penuh
                chunk_size = 1024 * 1024
                frames_written = 0
                
                while frames_written < max_frames:
                    frames_to_read = min(chunk_size, max_frames - frames_written)
                    data = in_wav.readframes(frames_to_read)
                    if not data:
                        break
                    out_wav.writeframes(data)
                    frames_written += frames_to_read
                    
        print(f"Berhasil dipotong: {os.path.basename(output_path)}")
        return True
    except Exception as e:
        print(f"Error memproses {input_path}: {e}")
        return False

# Target: 13:27 s.d. 15:30 = 2 jam 3 menit = 7380 detik
max_sec = 7380

files = [
    "/mnt/c/Users/rifra/MeetingRecordings/2026-08-08_1327_Meeting.mic.wav",
    "/mnt/c/Users/rifra/MeetingRecordings/2026-08-08_1327_Meeting.sys.wav"
]

print("Memulai proses pemotongan durasi audio...")

for original in files:
    if not os.path.exists(original):
        print(f"File tidak ditemukan: {original}")
        continue
        
    temp_out = original + ".trimmed.wav"
    success = trim_wav(original, temp_out, max_sec)
    
    if success:
        backup = original + ".backup"
        # Hapus backup lama jika kebetulan ada
        if os.path.exists(backup):
            os.remove(backup)
            
        print(f"Mencadangkan file asli ke .backup...")
        shutil.move(original, backup)
        
        print(f"Mengganti file asli dengan versi yang sudah dipotong...")
        shutil.move(temp_out, original)
        
print("Semua proses selesai!")
