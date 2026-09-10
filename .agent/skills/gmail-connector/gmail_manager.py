#!/usr/bin/env python3
"""
Gmail Manager
Provides listing, searching, reading, and basic management of Gmail messages.
"""
import os
import sys
import argparse
import base64
import signal
from email.mime.text import MIMEText
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Mail bodies routinely carry characters cp1252 cannot encode (narrow no-break
# space, smart quotes, emoji). On Windows that kills the print, not just the
# glyph, so force UTF-8 on the console streams.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

# Global timeout: 180 seconds
def timeout_handler(signum, frame):
    print("[ERROR] Gmail Manager timed out after 180 seconds", file=sys.stderr)
    sys.exit(1)

if os.name != 'nt': # signal.alarm is Unix-only
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(300)

# Determine the base directory
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# credentials.json is usually in the project root
BASE_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, '..', '..', '..'))
CREDENTIALS_FILE = os.path.join(BASE_DIR, '.agent', 'skills', 'work-drive-connector', 'credentials.json')
TOKEN_FILE = os.environ.get("GMAIL_TOKEN_FILE", os.path.join(SCRIPT_DIR, 'token_gmail_work.json'))

# Scopes - gmail.modify allows reading and managing messages (labels/archive)
SCOPES = ['https://www.googleapis.com/auth/gmail.modify']

def authenticate():
    """Authenticate and return credentials."""
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CREDENTIALS_FILE):
                print(f"Error: {CREDENTIALS_FILE} not found in {BASE_DIR}")
                return None
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            # Force redirect URI to match Work console settings
            flow.redirect_uri = 'http://localhost:8080/'
            
            # Manual code flow
            auth_url, _ = flow.authorization_url(prompt='consent', access_type='offline')
            print(f"\n[Gmail] Authentication Required!")
            print(f"1. Visit this URL in your browser:\n   {auth_url}")
            print(f"2. Authorize the application and copy the 'code' parameter from the resulting URL.")
            print(f"   (The page may fail to load, just copy the 'code=' value from the address bar)")
            
            code = input("\n[Gmail] Enter the authorization code: ").strip()
            flow.fetch_token(code=code)
            creds = flow.credentials
            
        # Save the credentials for the next run
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
    return creds

def list_emails(query=None, max_results=10):
    """List messages in the user's mailbox matching the query."""
    creds = authenticate()
    if not creds: return
    
    service = build('gmail', 'v1', credentials=creds)
    try:
        results = service.users().messages().list(userId='me', q=query, maxResults=max_results).execute()
        messages = results.get('messages', [])
        
        if not messages:
            print("No messages found.")
            return

        print(f"Found {len(messages)} messages:")
        for msg in messages:
            msg_id = msg['id']
            full_msg = service.users().messages().get(userId='me', id=msg_id, format='metadata', metadataHeaders=['Subject', 'From', 'Date']).execute()
            headers = full_msg.get('payload', {}).get('headers', [])
            
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '(No Subject)')
            sender = next((h['value'] for h in headers if h['name'] == 'From'), '(Unknown Sender)')
            date = next((h['value'] for h in headers if h['name'] == 'Date'), '(No Date)')
            
            print(f"- [{msg_id}] From: {sender} | Subject: {subject} | Date: {date}")
            
    except Exception as e:
        print(f"An error occurred: {e}")

def get_email(msg_id):
    """Get the full content of an email."""
    creds = authenticate()
    if not creds: return
    
    service = build('gmail', 'v1', credentials=creds)
    try:
        message = service.users().messages().get(userId='me', id=msg_id, format='full').execute()
        payload = message.get('payload', {})
        headers = payload.get('headers', [])
        
        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '(No Subject)')
        sender = next((h['value'] for h in headers if h['name'] == 'From'), '(Unknown Sender)')
        date = next((h['value'] for h in headers if h['name'] == 'Date'), '(No Date)')
        
        print(f"ID: {msg_id}")
        print(f"From: {sender}")
        print(f"Date: {date}")
        print(f"Subject: {subject}")
        print("-" * 40)
        
        # Simple body extraction
        body = ""
        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    data = part['body'].get('data')
                    if data:
                        body += base64.urlsafe_b64decode(data).decode()
        else:
            data = payload['body'].get('data')
            if data:
                body = base64.urlsafe_b64decode(data).decode()
        
        print(body if body else "(Empty body or HTML-only email)")
            
    except Exception as e:
        print(f"An error occurred: {e}")

def archive_email(msg_id):
    """Archive an email by removing the 'INBOX' label."""
    creds = authenticate()
    if not creds: return
    
    service = build('gmail', 'v1', credentials=creds)
    try:
        service.users().messages().modify(
            userId='me',
            id=msg_id,
            body={'removeLabelIds': ['INBOX']}
        ).execute()
        print(f"Message {msg_id} archived.")
    except Exception as e:
        print(f"An error occurred: {e}")

def get_profile():
    """Get the user's Gmail profile."""
    creds = authenticate()
    if not creds: return

    service = build('gmail', 'v1', credentials=creds)
    try:
        profile = service.users().getProfile(userId='me').execute()
        print(f"User: {profile.get('emailAddress')}")
        print(f"Total Messages: {profile.get('messagesTotal')}")
        print(f"Total Threads: {profile.get('threadsTotal')}")
    except Exception as e:
        print(f"An error occurred: {e}")

def send_email(to, subject, body, cc=None):
    """Send a plain-text email. gmail.modify scope is sufficient to send."""
    creds = authenticate()
    if not creds: return

    service = build('gmail', 'v1', credentials=creds)

    msg = MIMEText(body)
    msg['To'] = to
    if cc:
        msg['Cc'] = cc
    msg['Subject'] = subject
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()

    try:
        sent = service.users().messages().send(userId='me', body={'raw': raw}).execute()
        print(f"[OK] Email sent. Message ID: {sent.get('id')}")
        print(f"     To: {to}")
        if cc:
            print(f"     Cc: {cc}")
        print(f"     Subject: {subject}")
    except Exception as e:
        print(f"An error occurred: {e}")

# --- Headless two-step auth (for non-interactive shells) ---
# Mirrors authenticate()'s manual-code flow but split across two CLI calls so it
# works where stdin is unavailable. Produces the same token_gmail_work.json.

def _new_flow():
    # autogenerate_code_verifier=False disables PKCE so the two CLI steps stay
    # stateless (each runs in its own process; a per-run verifier would mismatch).
    flow = InstalledAppFlow.from_client_secrets_file(
        CREDENTIALS_FILE, SCOPES, autogenerate_code_verifier=False)
    flow.redirect_uri = 'http://localhost:8080/'
    return flow

def auth_url():
    """Print the OAuth authorization URL (step 1 of headless auth)."""
    if not os.path.exists(CREDENTIALS_FILE):
        print(f"Error: {CREDENTIALS_FILE} not found.")
        return
    flow = _new_flow()
    url, _ = flow.authorization_url(prompt='consent', access_type='offline')
    account_hint = os.environ.get('OWNER_WORK_EMAIL', 'you@yourcompany.com')
    print(f"[Gmail] Step 1 - authorize in a browser signed in as {account_hint}:")
    print(url)
    print("\nThe page will try to load http://localhost:8080/ and fail - that is expected.")
    print("Copy the 'code=' value from the address bar, then run:")
    print('  auth-save --code "PASTE_CODE_HERE"')

def auth_save(code):
    """Exchange an authorization code for a token (step 2 of headless auth)."""
    flow = _new_flow()
    flow.fetch_token(code=code)
    with open(TOKEN_FILE, 'w') as token:
        token.write(flow.credentials.to_json())
    print(f"[OK] Token saved to {TOKEN_FILE}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Gmail Manager')
    subparsers = parser.add_subparsers(dest='command')
    
    # Profile
    subparsers.add_parser('profile', help='Get user profile')
    
    # List/Search
    list_parser = subparsers.add_parser('list', help='List/Search emails')
    list_parser.add_argument('--query', help='Search query (e.g., "from:work")')
    list_parser.add_argument('--limit', type=int, default=10, help='Max results')
    
    # Get
    get_parser = subparsers.add_parser('get', help='Get full email content')
    get_parser.add_argument('id', help='Message ID')
    
    # Archive
    archive_parser = subparsers.add_parser('archive', help='Archive an email')
    archive_parser.add_argument('id', help='Message ID')

    # Send
    send_parser = subparsers.add_parser('send', help='Send a plain-text email')
    send_parser.add_argument('--to', required=True, help='Recipient(s), comma-separated')
    send_parser.add_argument('--cc', default=None, help='Cc recipient(s), comma-separated')
    send_parser.add_argument('--subject', required=True, help='Subject line')
    body_group = send_parser.add_mutually_exclusive_group(required=True)
    body_group.add_argument('--body', help='Inline body text')
    body_group.add_argument('--body-file', help='Path to a file containing the body text')

    # Headless auth
    subparsers.add_parser('auth-url', help='Print OAuth URL (step 1, headless auth)')
    auth_save_parser = subparsers.add_parser('auth-save', help='Exchange code for token (step 2)')
    auth_save_parser.add_argument('--code', required=True, help='Authorization code from redirect URL')

    args = parser.parse_args()

    if args.command == 'profile':
        get_profile()
    elif args.command == 'list':
        list_emails(query=args.query, max_results=args.limit)
    elif args.command == 'get':
        get_email(args.id)
    elif args.command == 'archive':
        archive_email(args.id)
    elif args.command == 'send':
        body = open(args.body_file).read() if args.body_file else args.body
        send_email(args.to, args.subject, body, cc=args.cc)
    elif args.command == 'auth-url':
        auth_url()
    elif args.command == 'auth-save':
        auth_save(args.code)
    else:
        parser.print_help()
