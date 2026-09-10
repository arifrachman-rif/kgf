"""
tray_watcher.py - Runs at Windows startup in the user's desktop session.
Polls for transcribing.lock and shows/hides the system tray icon automatically.
No interaction with the AI agent needed.
"""
import os
import sys
import time
import threading

try:
    import pystray
    from PIL import Image, ImageDraw
    USE_PYSTRAY = True
except ImportError:
    USE_PYSTRAY = False

LOCK_FILE = r"C:\Users\rifra\MeetingRecordings\transcribing.lock"
POLL_INTERVAL = 2  # seconds

def make_icon_image():
    """Create a simple blue circle with 'i' as the tray icon."""
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse([4, 4, size-4, size-4], fill=(30, 130, 230))
    draw.text((22, 12), "i", fill="white")
    return img

def run_pystray(stop_event):
    icon_img = make_icon_image()
    icon = pystray.Icon(
        "mom_watcher",
        icon_img,
        "MOM is underway...",
        menu=pystray.Menu(
            pystray.MenuItem("Transcribing meeting...", lambda: None, enabled=False)
        )
    )

    def poller():
        while not stop_event.is_set():
            if not os.path.exists(LOCK_FILE):
                icon.notify("MOM draft complete!", "Meeting Note-Taker")
                time.sleep(3)
                icon.stop()
                return
            time.sleep(POLL_INTERVAL)

    t = threading.Thread(target=poller, daemon=True)
    t.start()
    icon.run()

def run_winforms_fallback(stop_event):
    """Fallback: use Windows Forms NotifyIcon via subprocess if pystray not available."""
    import subprocess
    script = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "meeting-recorder", "tray_icon.ps1")
    subprocess.run(["powershell", "-WindowStyle", "Hidden", "-NoProfile",
                    "-ExecutionPolicy", "Bypass", "-File", script, LOCK_FILE])

def main():
    # Wait until lock file appears (up to 60s), then show icon
    for _ in range(30):
        if os.path.exists(LOCK_FILE):
            break
        time.sleep(2)
    else:
        sys.exit(0)  # lock never appeared, nothing to show

    stop_event = threading.Event()
    if USE_PYSTRAY:
        run_pystray(stop_event)
    else:
        run_winforms_fallback(stop_event)

if __name__ == "__main__":
    main()
