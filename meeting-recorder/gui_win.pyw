r"""Meeting Recorder GUI (Windows).

Small always-on-top window: type the meeting name, hit Start, hit Stop.
On stop it writes the sidecar metadata and (by default) kicks the WSL pipeline
(watcher.py --once) in the background, so the transcript + MOM draft appear in
the repo a few minutes later with no terminal involved.

Launch with Windows pythonw (no console), e.g. via the desktop shortcut
"Record Meeting" or:
  pythonw \\wsl.localhost\Ubuntu\...\meeting-recorder\gui_win.pyw
"""
import datetime
import json
import os
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import messagebox, ttk

# under pythonw stdout/stderr are None; imported modules print()
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import load_config, slugify           # noqa: E402
from recorder import ScreenRecorder, WindowsCapture, write_sidecar, now_stamp  # noqa: E402

WSL_REPO = "."
CREATE_NO_WINDOW = 0x08000000
TITLE_SKIP = ("prayer", "ooo", "focus block", "lunch")

def fetch_calendar_candidates():
    """Work calendar events near now (ongoing or starting within 30 min),
    nearest first. Returns [] on any failure — the GUI then keeps the default."""
    try:
        r = subprocess.run(
            ["wsl.exe", "-u", "you", "--", "bash", "-lc",
             f"cd {WSL_REPO} && python3 .agent/skills/google-calendar-connector/"
             "gcal_manager.py list --profile work --days-back 1 --days-forward 1 --json"],
            capture_output=True, text=True, timeout=90,
            creationflags=CREATE_NO_WINDOW)
        out = r.stdout
        start_idx = min((i for i in (out.find("["), out.find("{")) if i != -1),
                        default=-1)
        if start_idx < 0:
            return []
        events = json.loads(out[start_idx:])
    except Exception:
        return []
    now = datetime.datetime.now().astimezone()
    scored = []
    for ev in events:
        st, title = ev.get("start", ""), (ev.get("summary") or "").strip()
        if "T" not in st or not title:          # skip all-day/date-only
            continue
        if any(s in title.lower() for s in TITLE_SKIP):
            continue
        try:
            start = datetime.datetime.fromisoformat(st)
        except ValueError:
            continue
        delta_min = (now - start).total_seconds() / 60
        # ongoing (started up to 90 min ago) or starting within 30 min
        if -30 <= delta_min <= 90:
            scored.append((abs(delta_min), title))
    scored.sort()
    seen, out = set(), []
    for _, t in scored:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out

class App:
    def __init__(self, root):
        self.root = root
        self.cap = None
        self.screen = None
        self.base = None
        self.start_time = None
        cfg = load_config()
        self.rec_dir = cfg.get("machines", {}).get("windows", {}).get(
            "recordings_dir", r"F:\Meeting Recordings Automation")

        root.title("Meeting Recorder")
        root.geometry("360x330")
        root.attributes("-topmost", True)
        root.resizable(False, False)

        tk.Label(root, text="Meeting name:").pack(anchor="w", padx=12, pady=(10, 0))
        row = tk.Frame(root)
        row.pack(fill="x", padx=12)
        self.title_var = tk.StringVar(value="Meeting")
        self.entry = ttk.Combobox(row, textvariable=self.title_var,
                                  font=("Segoe UI", 11))
        self.entry.pack(side="left", fill="x", expand=True)
        self.refresh_btn = tk.Button(row, text="↻", width=3,
                                     command=self.refresh_calendar)
        self.refresh_btn.pack(side="left", padx=(6, 0))
        self.entry.focus()

        # Ad-hoc: a meeting the owner creates himself (Slack huddle, phone call).
        # Auto-ticks as soon as the typed title stops matching a calendar entry,
        # so the common case needs no thought; the tick can still be forced.
        self.adhoc_var = tk.BooleanVar(value=False)
        tk.Checkbutton(root, text="Ad-hoc meeting (not on calendar)",
                       variable=self.adhoc_var).pack(anchor="w", padx=12, pady=(4, 0))
        self.title_var.trace_add("write", self._on_title_typed)

        tk.Label(root, text="Attendees (optional, comma separated):").pack(
            anchor="w", padx=12, pady=(6, 0))
        self.attendees_var = tk.StringVar(value="")
        self.attendees = ttk.Entry(root, textvariable=self.attendees_var,
                                   font=("Segoe UI", 10))
        self.attendees.pack(fill="x", padx=12)

        self.button = tk.Button(root, text="●  Start Recording",
                                font=("Segoe UI", 13, "bold"),
                                bg="#1a7f37", fg="white", height=2,
                                command=self.toggle)
        self.button.pack(fill="x", padx=12, pady=10)

        self.status = tk.Label(root, text="Ready", fg="#555", justify="left")
        self.status.pack(anchor="w", padx=12)

        self.auto_var = tk.BooleanVar(value=True)
        tk.Checkbutton(root, text="Auto-process after stop (transcript + MOM via WSL)",
                       variable=self.auto_var).pack(anchor="w", padx=12, pady=(6, 0))
        self.video_var = tk.BooleanVar(value=False)
        tk.Checkbutton(root, text="Record video (screen, needs ffmpeg)",
                       variable=self.video_var).pack(anchor="w", padx=12)
        tk.Button(root, text="Open recordings folder", relief="groove",
                  command=lambda: os.startfile(self.rec_dir)).pack(anchor="w", padx=12, pady=6)

        root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.refresh_calendar()
        self.tick()

    def _on_title_typed(self, *_):
        """Title no longer matches a calendar candidate -> it is an ad-hoc
        meeting. Never un-ticks a box the owner ticked on purpose."""
        if self.cap is not None or self.adhoc_var.get():
            return
        current = self.title_var.get().strip()
        candidates = list(self.entry["values"])
        if current and candidates and current not in candidates:
            self.adhoc_var.set(True)

    def refresh_calendar(self):
        """Fetch calendar candidates in the background; safe to hit anytime."""
        self.refresh_btn.config(state="disabled")
        if not self.status["text"].startswith("Recording"):
            self.status.config(text="Checking calendar...", fg="#555")
        threading.Thread(target=self._load_calendar, daemon=True).start()

    def _load_calendar(self):
        candidates = fetch_calendar_candidates()

        def apply():
            self.refresh_btn.config(state="normal")
            if self.cap is not None:
                return  # recording; don't touch the title or status
            if not candidates:
                self.status.config(text="No calendar match, type a name", fg="#555")
                self.adhoc_var.set(True)
                return
            self.entry["values"] = candidates
            # prefill unless the owner typed something custom or ticked ad-hoc:
            # an ad-hoc title must never be overwritten by a calendar refresh
            current = self.title_var.get().strip()
            if not self.adhoc_var.get() and (
                    current in ("", "Meeting") or current in candidates):
                self.title_var.set(candidates[0])
            self._on_title_typed()
            self.status.config(
                text=("Ad-hoc, calendar ignored" if self.adhoc_var.get()
                      else f"Calendar: {len(candidates)} match"), fg="#555")

        self.root.after(0, apply)
        # idle auto-refresh every 5 minutes so a left-open window stays current
        self.root.after(300000, lambda: self.cap is None and self.refresh_calendar())

    def toggle(self):
        if self.cap is None:
            self.start()
        else:
            self.stop()

    def start(self):
        title = self.title_var.get().strip() or "meeting"
        os.makedirs(self.rec_dir, exist_ok=True)
        self.base = os.path.join(self.rec_dir, f"{now_stamp()}_{slugify(title)}")
        try:
            self.cap = WindowsCapture(self.base)
            devices = self.cap.start()
        except Exception as e:
            self.cap = None
            messagebox.showerror("Meeting Recorder", f"Cannot start capture:\n{e}")
            return
        self.screen = None
        if self.video_var.get():
            try:
                self.screen = ScreenRecorder(self.base)
                self.screen.start()
                devices.append("Screen: gdigrab -> .mp4")
            except FileNotFoundError:
                self.screen = None
                messagebox.showwarning("Meeting Recorder",
                                       "ffmpeg not found; recording audio only.")
        open(self.base + ".recording", "w").close()
        self.start_time = datetime.datetime.now(datetime.timezone.utc)
        self.button.config(text="■  Stop Recording", bg="#c62828")
        self.status.config(text="\n".join(devices), fg="#1a7f37")
        self.entry.config(state="disabled")
        self.attendees.config(state="disabled")

    def stop(self):
        title = self.title_var.get().strip() or "meeting"
        parts = self.cap.stop()
        self.cap = None
        if self.screen:
            video = self.screen.stop()
            self.screen = None
            if video:
                parts = list(parts) + [video]
        write_sidecar(self.base, title, self.start_time, parts, "windows",
                      ad_hoc=self.adhoc_var.get(),
                      attendees=self.attendees_var.get().split(","))
        marker = self.base + ".recording"
        if os.path.exists(marker):
            os.remove(marker)
        self.button.config(text="●  Start Recording", bg="#1a7f37")
        self.entry.config(state="normal")
        self.attendees.config(state="normal")
        msg = f"Saved: {os.path.basename(self.base)}"
        if self.auto_var.get():
            try:
                subprocess.Popen(
                    ["wsl.exe", "-u", "you", "--", "bash", "-lc",
                     f"cd {WSL_REPO} && python3 meeting-recorder/watcher.py --once "
                     f">> /tmp/meeting_watcher.log 2>&1"],
                    creationflags=CREATE_NO_WINDOW)
                msg += "\nProcessing started (transcript + MOM draft, check repo in a few min)"
            except Exception as e:
                msg += f"\nWSL processing failed to launch: {e}"
        self.status.config(text=msg, fg="#555")

    def tick(self):
        if self.cap is not None and self.start_time:
            el = int((datetime.datetime.now(datetime.timezone.utc)
                      - self.start_time).total_seconds())
            self.root.title(f"REC {el // 60:02d}:{el % 60:02d} - Meeting Recorder")
        else:
            self.root.title("Meeting Recorder")
        self.root.after(1000, self.tick)

    def on_close(self):
        if self.cap is not None:
            if not messagebox.askyesno("Meeting Recorder",
                                       "Still recording. Stop and save first?"):
                return
            self.stop()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
