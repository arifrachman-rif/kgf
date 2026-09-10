import sys
sys.path.append("meeting-recorder")
from common import load_gemini_key
GEMINI_BASE = "https://generativelanguage.googleapis.com"
import urllib.request
import json

key = load_gemini_key()
r = urllib.request.urlopen(f"{GEMINI_BASE}/v1beta/models?key={key}")
data = json.loads(r.read())
for m in data['models']:
    print(m['name'])
