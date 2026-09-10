"""
mom_tray_monitor.pyw - Autostart background monitor for MOM tray icon.

Drop into Windows Startup folder so it runs automatically when Windows starts.
Runs silently in the user's desktop session, watching for transcribing.lock.
When lock appears -> show tray icon. When lock disappears -> show "Done!" notify.

No console window (.pyw extension).
"""
import os
import sys
import time
import threading

LOCK_FILE = r"C:\Users\rifra\MeetingRecordings\transcribing.lock"
POLL_INTERVAL = 2  # seconds

def make_icon_image():
    """Blue circle icon using pillow."""
    from PIL import Image, ImageDraw, ImageFont
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # Blue circle
    draw.ellipse([2, 2, size-2, size-2], fill=(30, 130, 230))
    # White "i"
    draw.ellipse([28, 14, 36, 22], fill="white")   # dot
    draw.rectangle([28, 26, 36, 48], fill="white")  # stem
    return img

def run_icon():
    """Show the tray icon and wait until lock file disappears."""
    import pystray
    img = make_icon_image()
    icon = pystray.Icon(
        "mom_monitor",
        img,
        "MOM is underway...",
        menu=pystray.Menu(
            pystray.MenuItem("Transcribing meeting...", None, enabled=False)
        )
    )

    def poll():
        while True:
            if not os.path.exists(LOCK_FILE):
                icon.notify("MOM draft selesai!", "Meeting Note-Taker")
                time.sleep(4)
                icon.stop()
                return
            time.sleep(POLL_INTERVAL)

    t = threading.Thread(target=poll, daemon=True)
    t.start()
    icon.run()

def main():
    """Continuously watch for lock file. Show icon when it appears, hide when gone."""
    was_active = False
    while True:
        if os.path.exists(LOCK_FILE):
            if not was_active:
                was_active = True
                # Block here while icon is showing
                try:
                    run_icon()
                except Exception:
                    pass
                was_active = False
        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    main()
