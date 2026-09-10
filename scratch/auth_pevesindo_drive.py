import os
from google_auth_oauthlib.flow import InstalledAppFlow

CREDENTIALS_FILE = '.agent/skills/work-drive-connector/credentials.json'
SCOPES = ['https://www.googleapis.com/auth/drive']

flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES, autogenerate_code_verifier=False)
flow.redirect_uri = 'http://localhost:8080/'
auth_url, _ = flow.authorization_url(prompt='consent', access_type='offline')
print(f"URL:\n{auth_url}")
