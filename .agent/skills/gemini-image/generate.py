#!/usr/bin/env python3
"""Generate images via Google Gemini / Imagen API (the owner's key in token.env).

Two backends:
  - imagen-4.0-generate-001  (:predict)  -> clean poster gen, true aspectRatio control
  - gemini-3-pro-image / gemini-2.5-flash-image (:generateContent) -> "Nano Banana", best text/quality

Usage:
  python3 generate.py --prompt "..." --out path.png [--model imagen-4.0-generate-001] \
      [--aspect 3:4] [--n 1]
  python3 generate.py --prompt-file p.txt --out path.png --model gemini-3-pro-image

aspect (imagen only): 1:1 | 3:4 | 4:3 | 9:16 | 16:9
"""
import argparse, base64, json, os, sys, urllib.request, urllib.error

SKILL_DIR = os.path.dirname(os.path.abspath(__file__))
BASE = "https://generativelanguage.googleapis.com/v1beta/models"

def load_key():
    key = os.environ.get("GEMINI_API_KEY")
    if key:
        return key
    env_path = os.path.join(SKILL_DIR, "token.env")
    if os.path.exists(env_path):
        for line in open(env_path):
            line = line.strip()
            if line.startswith("GEMINI_API_KEY="):
                return line.split("=", 1)[1].strip()
    sys.exit("ERROR: no GEMINI_API_KEY (set env or token.env)")

def _post(url, body):
    req = urllib.request.Request(
        url, data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        sys.exit(f"ERROR {e.code}: {e.read().decode()[:600]}")

def _write(out, idx, total, raw_b64):
    base, ext = os.path.splitext(out)
    ext = ext or ".png"
    path = out if total == 1 else f"{base}_{idx + 1}{ext}"
    with open(path, "wb") as f:
        f.write(base64.b64decode(raw_b64))
    return path

def gen_imagen(prompt, out, model, aspect, n, key):
    url = f"{BASE}/{model}:predict?key={key}"
    body = {"instances": [{"prompt": prompt}],
            "parameters": {"sampleCount": n, "aspectRatio": aspect}}
    data = _post(url, body)
    preds = data.get("predictions", [])
    if not preds:
        sys.exit(f"No image returned: {json.dumps(data)[:400]}")
    return [_write(out, i, len(preds), p["bytesBase64Encoded"]) for i, p in enumerate(preds)]

def gen_gemini(prompt, out, model, key):
    url = f"{BASE}/{model}:generateContent?key={key}"
    body = {"contents": [{"parts": [{"text": prompt}]}]}
    data = _post(url, body)
    paths = []
    for cand in data.get("candidates", []):
        for part in cand.get("content", {}).get("parts", []):
            inline = part.get("inlineData") or part.get("inline_data")
            if inline and inline.get("data"):
                paths.append(_write(out, len(paths), 99, inline["data"]))
    if not paths:
        sys.exit(f"No image in response: {json.dumps(data)[:400]}")
    # fix single-file naming
    if len(paths) == 1 and paths[0] != out:
        os.replace(paths[0], out)
        paths = [out]
    return paths

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompt")
    ap.add_argument("--prompt-file")
    ap.add_argument("--out", required=True)
    ap.add_argument("--model", default="gemini-3-pro-image")
    ap.add_argument("--aspect", default="3:4")
    ap.add_argument("--n", type=int, default=1)
    a = ap.parse_args()

    prompt = a.prompt
    if a.prompt_file:
        prompt = open(a.prompt_file).read().strip()
    if not prompt:
        sys.exit("ERROR: provide --prompt or --prompt-file")

    key = load_key()
    if a.model.startswith("imagen"):
        paths = gen_imagen(prompt, a.out, a.model, a.aspect, a.n, key)
    else:
        paths = gen_gemini(prompt, a.out, a.model, key)
    for p in paths:
        print(f"OK: {p}  ({os.path.getsize(p)} bytes)")

if __name__ == "__main__":
    main()
