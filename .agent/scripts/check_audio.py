import wave
import contextlib
import os

files = [
    "/mnt/c/Users/rifra/MeetingRecordings/2026-08-08_1327_Meeting.mic.wav",
    "/mnt/c/Users/rifra/MeetingRecordings/2026-08-08_1327_Meeting.sys.wav"
]

for f in files:
    try:
        with contextlib.closing(wave.open(f, 'r')) as wf:
            frames = wf.getnframes()
            rate = wf.getframerate()
            duration = frames / float(rate)
            print(f"{os.path.basename(f)}: {duration} detik ({duration/3600:.2f} jam)")
    except Exception as e:
        print(f"Error on {f}: {e}")
