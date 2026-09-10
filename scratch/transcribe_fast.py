import os
import sys
import json
import time
import urllib.request
sys.path.append("meeting-recorder")
sys.path.append("meeting-recorder")
from common import load_gemini_key
GEMINI_BASE = "https://generativelanguage.googleapis.com"

def upload_file(path, mime, key):
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
    with urllib.request.urlopen(req_up, timeout=300) as r:
        info = json.loads(r.read())["file"]
        
    for _ in range(60):
        if info.get("state") == "ACTIVE":
            return info["uri"]
        time.sleep(5)
        req = urllib.request.Request(f"{GEMINI_BASE}/v1beta/{info['name']}",
                                     headers={"x-goog-api-key": key})
        with urllib.request.urlopen(req, timeout=60) as r:
            info = json.load(r)
    raise RuntimeError(f"File stuck in state {info.get('state')}")

def main():
    audio = "scratch/mutiara_1.mp3"
    out_md = "scratch/mutiara_transcript_1.md"
    key = load_gemini_key()
    
    print(f"Uploading {audio}...")
    uri = upload_file(audio, "audio/mp3", key)
    print(f"Uploaded to {uri}")
    
    prompt = """Transcribe this meeting recording completely and accurately.
The audio may mix English and Indonesian; transcribe each utterance in its
original language, do not translate.

Output format, one line per utterance, nothing else:
**[mm:ss]** Speaker N: text

Rules:
- Distinguish speakers by voice; label them Speaker 1, Speaker 2, ... consistently.
  If a speaker states their own name or is addressed by name, use that name instead.
- Do not summarize, skip, or clean up content. Include the full transcript."""
    
    body = {
        "contents": [{"parts": [{"file_data": {"mime_type": "audio/mp3", "file_uri": uri}}, {"text": prompt}]}],
        "generationConfig": {"temperature": 0.1, "maxOutputTokens": 65536}
    }
    
    print("Requesting transcription...")
    req = urllib.request.Request(
        f"{GEMINI_BASE}/v1beta/models/gemini-flash-latest:generateContent",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "x-goog-api-key": key},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=600) as r:
            data = json.loads(r.read())
    except urllib.error.HTTPError as e:
        print(f"HTTPError: {e.code} - {e.read().decode()}")
        sys.exit(1)
        
    text = data["candidates"][0]["content"]["parts"][0]["text"]
    
    with open(out_md, "w", encoding="utf-8") as f:
        f.write(text)
        
    print(f"DONE: Saved to {out_md}")

if __name__ == "__main__":
    main()
