#!/usr/bin/env python3
"""Transcription engine chain for the local meeting note-taker.

Chain (engine=auto): Gemini API (audio-in, returns speaker labels) -> whisper.cpp
on GPU (Vulkan on Radeon/Windows-Linux, Metal on Apple Silicon) as fallback when
Gemini is unavailable/fails. Gemini is preferred so transcripts carry speaker
labels instead of a single unlabelled stream. There is NO automatic CPU fallback:
the owner's rule. engine=cpu (explicit only) shells out to the legacy faster-whisper
script.

Usage:
  python3 transcribe.py --in recording.wav --out transcript.md \
      [--engine auto|whispercpp|cli|cpu] [--lang auto|en|id]

Output: markdown transcript with **[mm:ss]** timestamps (same format the /mom
pipeline already consumes) + a plain .txt sibling.
"""
import argparse
import base64
import datetime
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

from common import REPO_ROOT, detect_platform, fmt_ts, load_config, load_gemini_key

LOG_PATH = os.path.join(REPO_ROOT, "dashboard-data", "meeting_recorder_log.jsonl")
GEMINI_BASE = "https://generativelanguage.googleapis.com"
# Gemini audio pricing is folded into normal token pricing; log tokens + est cost.
GEMINI_PRICE_PER_MTOK = {"in": 0.30, "out": 2.50}  # flash-tier list price, USD

GEMINI_PROMPT = """Transcribe this meeting recording completely and accurately.
The audio may mix English and Indonesian; transcribe each utterance in its
original language, do not translate.

Output format, one line per utterance, nothing else:
**[mm:ss]** Speaker N: text

Rules:
- Timestamps are elapsed time from the start of the audio.
- Distinguish speakers by voice; label them Speaker 1, Speaker 2, ... consistently.
  If a speaker states their own name or is addressed by name, use that name instead.
- Do not summarize, skip, or clean up content. Include the full transcript.
"""

class EngineSkip(Exception):
    """This engine is unavailable/failed; try the next one in the chain."""

def log_row(row):
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    row["ts_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")

def _is_interop(bin_path):
    """True only when a Linux process shells out to a Windows .exe (WSL interop).

    A .exe target alone is not enough: running natively on Windows also targets
    .exe, but there the paths are already Windows paths and `wslpath` does not
    exist, so translating them raises WinError 2 instead."""
    return bin_path.lower().endswith(".exe") and detect_platform() == "wsl"

def _winpath(p):
    """WSL path -> Windows path for args passed to a Windows .exe via interop."""
    import subprocess
    return subprocess.run(["wslpath", "-w", p], capture_output=True,
                          text=True, check=True).stdout.strip()

def audio_duration(path, ffmpeg):
    ffprobe = os.path.join(os.path.dirname(ffmpeg), "ffprobe") if os.sep in ffmpeg else "ffprobe"
    if ffmpeg.lower().endswith(".exe"):
        ffprobe = ffprobe + ".exe" if not ffprobe.lower().endswith(".exe") else ffprobe
        if _is_interop(ffmpeg):
            path = _winpath(path)
    try:
        out = subprocess.run([ffprobe, "-v", "quiet", "-show_entries",
                              "format=duration", "-of", "csv=p=0", path],
                             capture_output=True, text=True, timeout=60).stdout.strip()
        return float(out)
    except Exception:
        return 0.0

# ---------- engine: whisper.cpp (GPU only) ----------

def run_whispercpp(audio, cfg, lang):
    machine = cfg["machine"]
    bin_path = machine.get("whispercpp_bin") or ""
    model = machine.get("whispercpp_model") or ""
    if not bin_path or not model or not os.path.exists(model):
        raise EngineSkip("whisper.cpp binary/model not configured on this machine")

    # A Windows .exe invoked from WSL can't read WSL-only paths (/tmp): keep the
    # temp files on a Windows drive and pass Windows-style path arguments.
    win_interop = _is_interop(bin_path)
    tmp_parent = os.path.dirname(bin_path) if win_interop else None

    ffmpeg = machine.get("ffmpeg", "ffmpeg")
    with tempfile.TemporaryDirectory(dir=tmp_parent) as td:
        wav16 = os.path.join(td, "audio16k.wav")
        subprocess.run([ffmpeg, "-y", "-v", "quiet", "-i", audio,
                        "-ac", "1", "-ar", "16000", wav16], check=True, timeout=600)
        prefix = os.path.join(td, "out")
        if win_interop:
            cmd = [bin_path, "-m", _winpath(model), "-f", _winpath(wav16),
                   "-oj", "-of", _winpath(prefix)]
        else:
            cmd = [bin_path, "-m", model, "-f", wav16, "-oj", "-of", prefix]
        if lang != "auto":
            cmd += ["-l", lang]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=3 * 3600)
        if r.returncode != 0:
            raise EngineSkip(f"whisper.cpp failed: {r.stderr[-300:]}")
        gpu_markers = ("Metal", "Vulkan", "CUDA", "gpu device")
        used_gpu = any(m.lower() in (r.stderr + r.stdout).lower() for m in gpu_markers)
        if cfg.get("require_gpu", True) and not used_gpu:
            raise EngineSkip("whisper.cpp ran without GPU (require_gpu on) -> skipping to CLI")
        with open(prefix + ".json", encoding="utf-8") as f:
            data = json.load(f)

    lines = []
    for seg in data.get("transcription", []):
        text = seg.get("text", "").strip()
        if not text:
            continue
        start_s = seg.get("offsets", {}).get("from", 0) / 1000.0
        lines.append(f"**[{fmt_ts(start_s)}]** {text}")
    if not lines:
        raise EngineSkip("whisper.cpp produced an empty transcript")
    return lines, f"whisper.cpp `{os.path.basename(model)}` (GPU)"

# ---------- engine: cli (Gemini API, audio-in) ----------

def _gemini_req(url, body, key, timeout=600):
    import subprocess
    import tempfile
    max_retries = 10
    backoff = 10
    for attempt in range(max_retries):
        tf_path = None
        try:
            with tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8") as tf:
                json.dump(body, tf)
                tf_path = tf.name
            cmd = ["curl", "-s", "-X", "POST",
                   "-H", "Content-Type: application/json",
                   "-H", f"x-goog-api-key: {key}",
                   "-d", f"@{tf_path}",
                   "--max-time", str(timeout), url]
            r = subprocess.run(cmd, capture_output=True, text=True, check=True)
            data = json.loads(r.stdout)
            if "error" in data:
                raise Exception(f"API Error: {data['error']}")
            return data
        except Exception as e:
            if attempt == max_retries - 1:
                raise e
            print(f"[transcribe] Request failed: {e}. Retrying in {backoff}s...", file=sys.stderr, flush=True)
            time.sleep(backoff)
            backoff *= 2
        finally:
            if tf_path and os.path.exists(tf_path):
                try: os.remove(tf_path)
                except: pass

def _gemini_upload_file(path, mime, key):
    """Files API resumable upload using curl; returns the file URI once ACTIVE."""
    size = os.path.getsize(path)
    filename = os.path.basename(path)
    
    req_start = urllib.request.Request(
        f"{GEMINI_BASE}/upload/v1beta/files?key={key}",
        data=json.dumps({"file": {"display_name": filename}}).encode(),
        headers={
            "X-Goog-Upload-Protocol": "resumable",
            "X-Goog-Upload-Command": "start",
            "X-Goog-Upload-Header-Content-Length": str(size),
            "X-Goog-Upload-Header-Content-Type": mime,
            "Content-Type": "application/json"
        },
        method="POST"
    )
    with urllib.request.urlopen(req_start, timeout=60) as r:
        upload_url = r.headers.get("X-Goog-Upload-URL")
    
    with open(path, "rb") as f:
        data = f.read()
        
    req_up = urllib.request.Request(
        upload_url,
        data=data,
        headers={
            "X-Goog-Upload-Command": "upload, finalize",
            "X-Goog-Upload-Offset": "0",
            "Content-Length": str(size)
        },
        method="POST"
    )
    try:
        with urllib.request.urlopen(req_up, timeout=300) as r:
            info = json.loads(r.read())["file"]
    except Exception as e:
        raise RuntimeError(f"Upload failed: {e}")
        
    # 3. Wait until processed (ACTIVE)
    for _ in range(60):
        if info.get("state") == "ACTIVE":
            return info["uri"]
        time.sleep(5)
        req = urllib.request.Request(f"{GEMINI_BASE}/v1beta/{info['name']}",
                                     headers={"x-goog-api-key": key})
        with urllib.request.urlopen(req, timeout=60) as r:
            info = json.load(r)
    raise EngineSkip(f"Gemini file stuck in state {info.get('state')}")

def run_gemini(audio, cfg, lang):
    key = load_gemini_key()
    machine = cfg["machine"]
    ffmpeg = machine.get("ffmpeg", "ffmpeg")
    model = cfg.get("gemini_model", "gemini-2.5-flash")

    import wave
    import re
    duration = 0
    try:
        # Run ffmpeg -i to extract the duration from the stderr output
        r_dur = subprocess.run([ffmpeg, "-i", audio], capture_output=True, text=True, timeout=15)
        match = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", r_dur.stderr)
        if match:
            h, m, s = match.groups()
            duration = int(h) * 3600 + int(m) * 60 + float(s)
        elif audio.lower().endswith(".wav"):
            with wave.open(audio, "rb") as wf:
                duration = wf.getnframes() / float(wf.getframerate())
    except Exception as e:
        print(f"[transcribe] failed to read duration via ffmpeg/wave: {e}", file=sys.stderr)

    parts_dir = audio + ".parts"
    os.makedirs(parts_dir, exist_ok=True)

    with tempfile.TemporaryDirectory() as td:
        # 5-minute chunks by default. On a metered/free-tier key the request
        # COUNT is the scarce resource, not the tokens, so `chunk_sec` lets a
        # long meeting be sent as a few big chunks instead of dozens of small
        # ones. Gemini bills audio at ~32 tok/sec, so even 30 min is ~58k tokens.
        # CHUNK_SEC in the environment wins, so a one-off long meeting can be
        # sent as fewer, bigger requests when the daily request quota is tight,
        # without editing the owner's config.
        chunk_duration = int(os.environ.get("CHUNK_SEC") or cfg.get("chunk_sec", 300))
        if duration > chunk_duration + 30:  # Allow 30s buffer to avoid tiny tail chunks
            num_chunks = int(duration // chunk_duration) + (1 if duration % chunk_duration > 0 else 0)
            chunks = []
            for i in range(num_chunks):
                start_time = i * chunk_duration
                chunks.append((i, start_time))
            print(f"[transcribe] Audio duration ({duration/60:.1f} min) exceeds limit. Split into {len(chunks)} chunks.", flush=True)
        else:
            chunks = [(0, 0)]
            chunk_duration = duration

        total_in_tok = 0
        total_out_tok = 0
        total_cost = 0.0
        all_lines = []
        
        import concurrent.futures

        def process_chunk(idx, start_time):
            chunk_txt = os.path.join(parts_dir, f"chunk_{idx}.txt")
            if os.path.exists(chunk_txt):
                with open(chunk_txt, "r", encoding="utf-8") as f:
                    cached_lines = f.read().splitlines()
                print(f"[transcribe] Resuming Part {idx + 1}/{len(chunks)} from cache...", flush=True)
                return idx, cached_lines, 0, 0, 0.0

            # extract chunk and compress to ogg/opus 16k mono
            chunk_wav = os.path.join(td, f"chunk_{idx}.wav")
            
            win_interop = _is_interop(ffmpeg)
            def _wp(p): return _winpath(p) if win_interop else p

            if len(chunks) > 1:
                subprocess.run([ffmpeg, "-y", "-v", "quiet", "-nostdin", "-ss", str(start_time), "-t", str(chunk_duration),
                                "-i", _wp(audio), "-c", "copy", _wp(chunk_wav)], check=True, timeout=180)
            else:
                chunk_wav = audio
                
            ogg = os.path.join(td, f"audio_{idx}.ogg")
            subprocess.run([ffmpeg, "-y", "-v", "quiet", "-nostdin", "-i", _wp(chunk_wav), "-ac", "1",
                            "-ar", "16000", "-c:a", "libopus", "-b:a", "24k", _wp(ogg)],
                           check=True, timeout=600)
            size = os.path.getsize(ogg)
            prompt = GEMINI_PROMPT
            if lang != "auto":
                prompt += f"\nThe meeting is primarily in '{lang}'."
            if len(chunks) > 1:
                prompt += f"\nThis is Part {idx + 1} of {len(chunks)} of the meeting. Keep speaker labels consistent if possible."

            if size < 15 * 1024 * 1024:  # inline under the ~20MB API payload limit
                audio_part = {"inline_data": {
                    "mime_type": "audio/ogg",
                    "data": base64.b64encode(open(ogg, "rb").read()).decode()}}
            else:
                uri = _gemini_upload_file(ogg, "audio/ogg", key)
                audio_part = {"file_data": {"mime_type": "audio/ogg", "file_uri": uri}}

            text = None
            for temp in [0.1, 0.3, 0.5]:
                body = {"contents": [{"parts": [audio_part, {"text": prompt}]}],
                        "generationConfig": {"temperature": temp, "maxOutputTokens": 65536}}
                try:
                    data = _gemini_req(f"{GEMINI_BASE}/v1beta/models/{model}:generateContent",
                                       body, key, timeout=180)
                except Exception as e:
                    raise EngineSkip(f"Gemini API error on Part {idx + 1}: {e}")

                cand = data.get("candidates", [{}])[0]
                reason = cand.get("finishReason", "")
                if reason == "RECITATION":
                    print(f"[transcribe] Recitation block triggered on Part {idx + 1} at temp {temp}. Retrying with higher temperature...", flush=True)
                    continue

                try:
                    text = cand["content"]["parts"][0]["text"]
                    break
                except (KeyError, IndexError):
                    if reason and reason != "STOP":
                        print(f"[transcribe] Blocked by safety/other reason on Part {idx + 1}: {reason}. Retrying with higher temperature...", flush=True)
                        continue
                    raise EngineSkip(f"Gemini returned no text on Part {idx + 1}: {json.dumps(data)[:300]}")

            if not text:
                raise EngineSkip(f"Gemini transcription failed due to safety/recitation blocks on Part {idx + 1}")

            usage = data.get("usageMetadata", {})
            in_tok = usage.get("promptTokenCount", 0)
            out_tok = usage.get("candidatesTokenCount", 0)
            cost = (in_tok * GEMINI_PRICE_PER_MTOK["in"] +
                    out_tok * GEMINI_PRICE_PER_MTOK["out"]) / 1e6
            
            lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
            if lines:
                with open(chunk_txt, "w", encoding="utf-8") as f:
                    f.write("\n".join(lines))
            
            print(f"[transcribe] Completed Part {idx + 1}/{len(chunks)}", flush=True)
            return idx, lines, in_tok, out_tok, cost

        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(chunks), 15)) as executor:
            futures = {executor.submit(process_chunk, idx, st): idx for idx, st in chunks}
            for future in concurrent.futures.as_completed(futures):
                try:
                    results.append(future.result())
                except Exception as e:
                    raise EngineSkip(f"Thread failed: {e}")

        results.sort(key=lambda x: x[0])
        total_in_tok = sum(r[2] for r in results)
        total_out_tok = sum(r[3] for r in results)
        total_cost = sum(r[4] for r in results)
        
        all_lines = []
        for idx, lines, _, _, _ in results:
            if not lines: continue
            if len(chunks) > 1:
                all_lines.append(f"\n--- [PART {idx + 1} OF {len(chunks)}] ---\n")
            all_lines.extend(lines)

        # log consolidated usage
        log_row({"kind": "transcribe", "engine": f"gemini:{model}",
                 "file": os.path.basename(audio), "in_tok": total_in_tok,
                 "out_tok": total_out_tok, "est_usd": round(total_cost, 4)})

        if not all_lines:
            raise EngineSkip("Gemini transcript empty")
            
        try:
            import shutil
            shutil.rmtree(parts_dir)
        except Exception:
            pass
            
        return all_lines, f"Gemini `{model}` (audio-in, speaker labels, ~${total_cost:.3f})"

# ---------- engine: cpu (explicit only, legacy faster-whisper) ----------

def run_cpu(audio, cfg, lang, out_md):
    venv_py = "python3"
    script = os.path.join(REPO_ROOT, "scripts", "transcribe_audio.py")
    subprocess.run([venv_py, script, "--in", audio, "--out", out_md,
                    "--model", "small", "--lang", lang], check=True)
    return None, "faster-whisper small (cpu, explicit)"

# ---------- orchestration ----------

def transcribe(audio, out_md, engine=None, lang=None, cfg=None):
    """Returns (out_md, engine_note). Raises RuntimeError if all engines fail."""
    if os.path.isfile(out_md) and os.path.getsize(out_md) > 100:
        note = "cached"
        try:
            with open(out_md, "r", encoding="utf-8") as f:
                for _ in range(5):
                    line = f.readline()
                    if line.startswith("- Engine:"):
                        note = line.split(":", 1)[1].strip() + " (cached)"
                        break
        except Exception:
            pass
        print(f"[transcribe] OK (reusing existing transcript) -> {out_md}", flush=True)
        return out_md, note

    cfg = cfg or load_config()
    engine = engine or cfg.get("engine", "auto")
    lang = lang or cfg.get("language", "auto")

    # auto prefers Gemini (audio-in, speaker labels); whisper.cpp is the fallback
    # if Gemini is unavailable/fails. NEVER falls back to CPU (the owner's rule).
    chain = {"auto": ["cli", "whispercpp"],
             "whispercpp": ["whispercpp"],
             "cli": ["cli"],
             "cpu": ["cpu"]}[engine]

    errors = []
    for eng in chain:
        try:
            print(f"[transcribe] trying engine: {eng}", flush=True)
            if eng == "cpu":
                run_cpu(audio, cfg, lang, out_md)
                return out_md, "faster-whisper (cpu, explicit)"
            fn = run_whispercpp if eng == "whispercpp" else run_gemini
            lines, note = fn(audio, cfg, lang)
            dur = audio_duration(audio, cfg["machine"].get("ffmpeg", "ffmpeg"))
            header = (f"# Transcript: {os.path.basename(audio)}\n\n"
                      f"- Engine: {note}\n"
                      f"- Audio duration: {fmt_ts(dur)}\n"
                      f"- Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n---\n\n")
            os.makedirs(os.path.dirname(os.path.abspath(out_md)) or ".", exist_ok=True)
            with open(out_md, "w", encoding="utf-8") as f:
                f.write(header + "\n".join(lines) + "\n")
            txt = os.path.splitext(out_md)[0] + ".txt"
            with open(txt, "w", encoding="utf-8") as f:
                f.write("\n".join(lines) + "\n")
            print(f"[transcribe] OK via {eng} -> {out_md}", flush=True)
            return out_md, note
        except EngineSkip as e:
            print(f"[transcribe] {eng} skipped: {e}", file=sys.stderr, flush=True)
            errors.append(f"{eng}: {e}")
        except (subprocess.SubprocessError, OSError) as e:
            print(f"[transcribe] {eng} error: {e}", file=sys.stderr, flush=True)
            errors.append(f"{eng}: {e}")
    raise RuntimeError("all engines failed: " + " | ".join(errors))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--out", dest="out", required=True)
    ap.add_argument("--engine", choices=["auto", "whispercpp", "cli", "cpu"])
    ap.add_argument("--lang", choices=["auto", "en", "id"])
    args = ap.parse_args()
    if not os.path.isfile(args.inp):
        sys.exit(f"ERROR: input not found: {args.inp}")
    out, note = transcribe(args.inp, args.out, args.engine, args.lang)
    print(f"DONE: {out} ({note})")

if __name__ == "__main__":
    main()
