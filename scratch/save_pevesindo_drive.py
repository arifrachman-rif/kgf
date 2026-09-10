import sys
from google_auth_oauthlib.flow import InstalledAppFlow

CREDENTIALS_FILE = '.agent/skills/work-drive-connector/credentials.json'
TOKEN_FILE = '.agent/skills/secondary-drive-connector/token.json'
SCOPES = ['https://www.googleapis.com/auth/drive']

if len(sys.argv) < 2:
    print("Usage: python script.py <CODE>")
    sys.exit(1)

code = sys.argv[1]

flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES, autogenerate_code_verifier=False)
flow.redirect_uri = 'http://localhost:8080/'
flow.fetch_token(code=code)

with open(TOKEN_FILE, 'w') as f:
    f.write(flow.credentials.to_json())

print("[OK] Drive token saved successfully to secondary-drive-connector!")
