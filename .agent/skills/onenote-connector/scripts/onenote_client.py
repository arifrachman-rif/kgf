#!/usr/bin/env python3
"""
onenote_client.py: Syncs pages, daily logs, and weekly reflections from Microsoft OneNote.
Uses Microsoft Graph API via OAuth 2.0 Device Code Flow.
"""
import os
import sys
import json
import time
import urllib.request
import urllib.parse
from datetime import datetime
from html.parser import HTMLParser

# Windows consoles default to cp1252, which cannot encode the box-drawing and
# arrow glyphs used in the progress output. Force UTF-8 so the script behaves
# the same on Windows as it does under WSL.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

# ── Paths ────────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
# Repo root: .agent/skills/onenote-connector -> .agent/skills -> .agent -> root
BASE_DIR = os.path.abspath(os.path.join(SKILL_DIR, "..", "..", ".."))

TOKEN_ENV_PATH = os.path.join(SKILL_DIR, "token.env")
TOKEN_JSON_PATH = os.path.join(SKILL_DIR, "token.json")
CONFIG_JSON_PATH = os.path.join(SKILL_DIR, "config.json")

# ── HTML to Markdown Parser ──────────────────────────────────────────
class OneNoteHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.markdown = []
        self.list_stack = []
        self.in_title = False
        self.in_head = False
        self.in_style = False
        self.current_tag = None
        self.current_attrs = {}

    def handle_starttag(self, tag, attrs):
        self.current_tag = tag
        self.current_attrs = dict(attrs)
        
        if tag == 'head':
            self.in_head = True
        elif tag == 'style':
            self.in_style = True
        elif tag == 'title':
            self.in_title = True
        elif tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            level = int(tag[1])
            self.markdown.append("\n" + "#" * level + " ")
        elif tag == 'p':
            todo_tag = self.current_attrs.get('data-tag', '')
            if todo_tag == 'to-do':
                self.markdown.append("\n- [ ] ")
            elif todo_tag == 'to-do:completed':
                self.markdown.append("\n- [x] ")
            else:
                self.markdown.append("\n")
        elif tag == 'ul':
            self.list_stack.append('*')
            self.markdown.append("\n")
        elif tag == 'ol':
            self.list_stack.append(1)
            self.markdown.append("\n")
        elif tag == 'li':
            if not self.list_stack:
                self.markdown.append("\n* ")
            else:
                list_type = self.list_stack[-1]
                if list_type == '*':
                    self.markdown.append(f"\n{'  ' * (len(self.list_stack)-1)}* ")
                else:
                    self.markdown.append(f"\n{'  ' * (len(self.list_stack)-1)}{list_type}. ")
                    self.list_stack[-1] += 1
        elif tag == 'a':
            href = self.current_attrs.get('href', '')
            self.markdown.append(f"[")
        elif tag == 'img':
            alt = self.current_attrs.get('alt', 'image')
            src = self.current_attrs.get('src', '')
            self.markdown.append(f"\n![{alt}]({src})\n")
        elif tag in ['strong', 'b']:
            self.markdown.append("**")
        elif tag in ['em', 'i']:
            self.markdown.append("*")

    def handle_endtag(self, tag):
        if tag == 'head':
            self.in_head = False
        elif tag == 'style':
            self.in_style = False
        elif tag == 'title':
            self.in_title = False
        elif tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p']:
            self.markdown.append("\n")
        elif tag in ['ul', 'ol']:
            if self.list_stack:
                self.list_stack.pop()
            self.markdown.append("\n")
        elif tag == 'a':
            href = self.current_attrs.get('href', '')
            self.markdown.append(f"]({href})")
        elif tag in ['strong', 'b']:
            self.markdown.append("**")
        elif tag in ['em', 'i']:
            self.markdown.append("*")
            
        self.current_tag = None
        self.current_attrs = {}

    def handle_data(self, data):
        if self.in_head or self.in_style or self.in_title:
            return
        
        # Replace non-breaking spaces and strip outer whitespace for clean formatting
        cleaned = data.replace('\xa0', ' ')
        if cleaned:
            self.markdown.append(cleaned)

    def get_markdown(self):
        content = "".join(self.markdown)
        # Clean up double newlines but preserve paragraph splits
        lines = []
        for line in content.splitlines():
            # Strip trailing space but keep markdown formatting
            lines.append(line.rstrip())
        
        # Merge consecutive blank lines
        merged = []
        last_was_blank = False
        for line in lines:
            if not line:
                if not last_was_blank:
                    merged.append("")
                    last_was_blank = True
            else:
                merged.append(line)
                last_was_blank = False
                
        return "\n".join(merged).strip()

# ── Microsoft Graph Helper ───────────────────────────────────────────
class MicrosoftGraphClient:
    def __init__(self):
        self.client_id = self.load_client_id()
        self.tokens = self.load_tokens()
        self.graph_url = "https://graph.microsoft.com/v1.0"

    def load_client_id(self):
        # Load from token.env first
        if os.path.exists(TOKEN_ENV_PATH):
            with open(TOKEN_ENV_PATH, "r") as f:
                for line in f:
                    if line.startswith("ONENOTE_CLIENT_ID="):
                        return line.split("=", 1)[1].strip()
        
        # Fallback to root .env
        root_env_path = os.path.join(BASE_DIR, ".env")
        if os.path.exists(root_env_path):
            with open(root_env_path, "r") as f:
                for line in f:
                    if line.startswith("ONENOTE_CLIENT_ID="):
                        return line.split("=", 1)[1].strip()
        
        # No default client ID because first-party apps (like PowerShell / CLI) fail consent checks for OneNote scopes on personal accounts.
        # User must configure their own client ID.
        return None

    def load_tokens(self):
        if os.path.exists(TOKEN_JSON_PATH):
            try:
                with open(TOKEN_JSON_PATH, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return None

    def save_tokens(self, tokens):
        self.tokens = tokens
        os.makedirs(os.path.dirname(TOKEN_JSON_PATH), exist_ok=True)
        with open(TOKEN_JSON_PATH, "w") as f:
            json.dump(tokens, f, indent=2)

    def request(self, url, method="GET", headers=None, data=None, is_json=True):
        if headers is None:
            headers = {}
        
        if self.tokens and "access_token" in self.tokens:
            headers["Authorization"] = f"Bearer {self.tokens['access_token']}"
        
        req_data = None
        if data:
            if isinstance(data, dict):
                req_data = urllib.parse.urlencode(data).encode("utf-8")
                if "Content-Type" not in headers:
                    headers["Content-Type"] = "application/x-www-form-urlencoded"
            else:
                req_data = data
                
        req = urllib.request.Request(url, headers=headers, data=req_data, method=method)
        
        try:
            with urllib.request.urlopen(req) as response:
                content = response.read()
                if is_json:
                    return json.loads(content.decode("utf-8"))
                return content.decode("utf-8")
        except urllib.error.HTTPError as e:
            # Handle token expiry/refresh if access_token exists
            if e.code == 401 and self.tokens and "refresh_token" in self.tokens:
                print("      [Token] Access token expired, attempting refresh...", flush=True)
                if self.refresh_access_token():
                    # Retry once
                    headers["Authorization"] = f"Bearer {self.tokens['access_token']}"
                    req = urllib.request.Request(url, headers=headers, data=req_data, method=method)
                    with urllib.request.urlopen(req) as retry_response:
                        content = retry_response.read()
                        if is_json:
                            return json.loads(content.decode("utf-8"))
                        return content.decode("utf-8")
            
            err_msg = e.read().decode("utf-8")
            try:
                err_json = json.loads(err_msg)
                print(f"      [API Error] {e.code} - {err_json.get('error', {}).get('message', e.reason)}")
            except Exception:
                print(f"      [API Error] {e.code} - {e.reason} ({err_msg})")
            raise e

    def device_flow_auth(self):
        if not self.client_id:
            print("\n[ERROR] ONENOTE_CLIENT_ID not found in token.env or .env.")
            print("Please register a client ID. Instructions are in docs/ONENOTE.md.")
            sys.exit(1)

        print(f"\n[1/3] Initiating Device Flow authorization using Client ID: {self.client_id}...", flush=True)
        url = "https://login.microsoftonline.com/common/oauth2/v2.0/devicecode"
        scopes = "Notes.Read Notes.ReadWrite Notes.Read.All Notes.ReadWrite.All offline_access"
        
        payload = {
            "client_id": self.client_id,
            "scope": scopes
        }
        
        try:
            resp = self.request(url, method="POST", data=payload)
        except Exception as e:
            print(f"Failed to start device flow: {e}")
            sys.exit(1)
            
        user_code = resp["user_code"]
        device_code = resp["device_code"]
        verification_uri = resp["verification_uri"]
        interval = resp.get("interval", 5)
        expires_in = resp.get("expires_in", 900)
        
        print("\n" + "=" * 60)
        print("MICROSOFT ONENOTE AUTHENTICATION")
        print("=" * 60)
        print(f"1. Open your browser and visit:")
        print(f"   {verification_uri}")
        print(f"\n2. Enter this code when prompted:")
        print(f"   {user_code}")
        print("=" * 60 + "\n")
        print("Waiting for authentication...", flush=True)
        
        # Poll for token
        token_url = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
        poll_payload = {
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
            "client_id": self.client_id,
            "device_code": device_code
        }
        
        start_time = time.time()
        while time.time() - start_time < expires_in:
            time.sleep(interval)
            try:
                # Need to use standard urlopen without our auth headers for token endpoint
                req_data = urllib.parse.urlencode(poll_payload).encode("utf-8")
                req = urllib.request.Request(
                    token_url, 
                    headers={"Content-Type": "application/x-www-form-urlencoded"}, 
                    data=req_data, 
                    method="POST"
                )
                with urllib.request.urlopen(req) as r:
                    token_resp = json.loads(r.read().decode("utf-8"))
                    print("\n✓ Authentication successful! Saving tokens.", flush=True)
                    self.save_tokens(token_resp)
                    return True
            except urllib.error.HTTPError as e:
                err_msg = e.read().decode("utf-8")
                try:
                    err_json = json.loads(err_msg)
                    err_code = err_json.get("error")
                    if err_code == "authorization_pending":
                        print(".", end="", flush=True)
                        continue
                    elif err_code == "code_expired":
                        print("\n❌ Code expired. Please run auth command again.")
                        break
                    else:
                        print(f"\n❌ Error polling token: {err_code} - {err_json.get('error_description')}")
                        break
                except Exception:
                    print(f"\n❌ HTTP Error {e.code}")
                    break
        sys.exit(1)

    def refresh_access_token(self):
        if not self.tokens or "refresh_token" not in self.tokens:
            return False
            
        token_url = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
        scopes = "Notes.Read Notes.ReadWrite Notes.Read.All Notes.ReadWrite.All offline_access"
        payload = {
            "grant_type": "refresh_token",
            "client_id": self.client_id,
            "refresh_token": self.tokens["refresh_token"],
            "scope": scopes
        }
        
        try:
            req_data = urllib.parse.urlencode(payload).encode("utf-8")
            req = urllib.request.Request(
                token_url, 
                headers={"Content-Type": "application/x-www-form-urlencoded"}, 
                data=req_data, 
                method="POST"
            )
            with urllib.request.urlopen(req) as r:
                resp = json.loads(r.read().decode("utf-8"))
                # Merge new tokens (some refresh calls don't return a new refresh token, preserve old one if so)
                merged_tokens = self.tokens.copy()
                merged_tokens.update(resp)
                self.save_tokens(merged_tokens)
                return True
        except Exception as e:
            print(f"      [Token] Refresh failed: {e}")
            return False

# ── Main Implementation ───────────────────────────────────────────────
def get_config():
    if os.path.exists(CONFIG_JSON_PATH):
        try:
            with open(CONFIG_JSON_PATH, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def translate_month(month_int):
    months = {
        1: ("Januari", "January"),
        2: ("Februari", "February"),
        3: ("Maret", "March"),
        4: ("April", "April"),
        5: ("Mei", "May"),
        6: ("Juni", "June"),
        7: ("Juli", "July"),
        8: ("Agustus", "August"),
        9: ("September", "September"),
        10: ("Oktoba", "October"), # Indonesian variants
        11: ("November", "November"),
        12: ("Desember", "December")
    }
    # Standard spelling adjustments
    if month_int == 10:
        return "Oktober", "October"
    return months.get(month_int, ("", ""))

def sync_journal(client, dry_run=False):
    print("\n[OneNote] Synchronizing daily logs & weekly reflections...", flush=True)
    config = get_config()
    
    # Identify target monthly section name candidates
    now = datetime.now()
    month_id, month_en = translate_month(now.month)
    year = now.year
    
    # Candidates for section names:
    # E.g. "Juli 2026", "July 2026", "2026-07", "07-2026", "Juli"
    # Also the abbreviated form the owner actually uses in "2026 Book": "Jul 26"
    yy = str(year)[-2:]
    candidates = [
        f"{month_id} {year}",
        f"{month_en} {year}",
        f"{year}-{now.month:02d}",
        f"{now.month:02d}-{year}",
        f"{month_en[:3]} {yy}",
        f"{month_id[:3]} {yy}",
        f"{month_en[:3]} {year}",
        f"{month_id[:3]} {year}",
        month_id,
        month_en
    ]
    
    journal_notebook = config.get("journal_notebook", "")
    journal_section_group = config.get("journal_section_group", "")
    
    # 1. Get notebooks
    try:
        notebooks = client.request(f"{client.graph_url}/me/onenote/notebooks")["value"]
    except Exception as e:
        print(f"❌ Failed to fetch notebooks: {e}. Run 'auth' first.")
        return
        
    target_notebook_id = None
    if journal_notebook:
        for nb in notebooks:
            if nb["displayName"].lower() == journal_notebook.lower():
                target_notebook_id = nb["id"]
                break
        if not target_notebook_id:
            print(f"⚠️ Notebook '{journal_notebook}' not found. Searching all sections.")
    
    sections = []
    
    # 2. Get sections (either inside a notebook/group or globally)
    # If a notebook is identified, fetch its sections
    if target_notebook_id:
        # Check if inside a section group
        if journal_section_group:
            try:
                groups = client.request(f"{client.graph_url}/me/onenote/notebooks/{target_notebook_id}/sectionGroups")["value"]
                target_group_id = None
                for gp in groups:
                    if gp["displayName"].lower() == journal_section_group.lower():
                        target_group_id = gp["id"]
                        break
                if target_group_id:
                    sections = client.request(f"{client.graph_url}/me/onenote/sectionGroups/{target_group_id}/sections")["value"]
                else:
                    print(f"⚠️ Section Group '{journal_section_group}' not found. Fetching notebook sections.")
                    sections = client.request(f"{client.graph_url}/me/onenote/notebooks/{target_notebook_id}/sections")["value"]
            except Exception:
                sections = client.request(f"{client.graph_url}/me/onenote/notebooks/{target_notebook_id}/sections")["value"]
        else:
            sections = client.request(f"{client.graph_url}/me/onenote/notebooks/{target_notebook_id}/sections")["value"]
    else:
        # Global search: get all sections
        try:
            sections = client.request(f"{client.graph_url}/me/onenote/sections")["value"]
        except Exception as e:
            print(f"❌ Failed to fetch sections: {e}")
            return

    # Find the section that matches our month candidates
    target_section = None
    for sec in sections:
        name = sec["displayName"].strip().lower()
        if any(c.lower() == name or c.lower() in name for c in candidates):
            target_section = sec
            break
            
    if not target_section:
        # Fallback: list all section names so the user can verify
        available_sections = [s["displayName"] for s in sections]
        print(f"⚠️ No active monthly section found for {month_id} {year}.")
        print(f"   Month candidates searched: {candidates}")
        print(f"   Available sections: {available_sections}")
        print("   If you have a section for this month, make sure its name matches one of the candidates.")
        return

    print(f"   Found target section: '{target_section['displayName']}' in OneNote", flush=True)
    
    # 3. Get pages inside target section
    try:
        pages = client.request(f"{client.graph_url}/me/onenote/sections/{target_section['id']}/pages")["value"]
    except Exception as e:
        print(f"❌ Failed to fetch pages for section {target_section['displayName']}: {e}")
        return
        
    print(f"   Syncing {len(pages)} pages to local journal...", flush=True)
    
    # Target directory: journal/onenote/YYYY-MM/
    dest_dir = os.path.join(BASE_DIR, "journal", "onenote", f"{year}-{now.month:02d}")
    if not dry_run:
        os.makedirs(dest_dir, exist_ok=True)
        
    synced_pages = []
    
    for page in pages:
        title = page["title"].strip()
        if not title:
            title = "Untitled Page"
        
        # Clean file name
        safe_title = "".join(c for c in title if c.isalnum() or c in " -_").strip()
        filename = f"{safe_title}.md"
        dest_path = os.path.join(dest_dir, filename)
        
        print(f"      ▸ Page: '{title}' -> journal/onenote/{year}-{now.month:02d}/{filename}...", end=" ", flush=True)
        
        if dry_run:
            print("✓ (dry-run)")
            synced_pages.append({"title": title, "path": dest_path})
            continue
            
        try:
            # Fetch page content HTML
            content_html = client.request(
                f"{client.graph_url}/me/onenote/pages/{page['id']}/content?includeIDs=true",
                is_json=False
            )
            
            # Convert HTML to Markdown
            parser = OneNoteHTMLParser()
            parser.feed(content_html)
            markdown = parser.get_markdown()
            
            # Prepend title and metadata block
            md_content = f"# {title}\n\n"
            md_content += f"> **OneNote Page ID**: `{page['id']}`\n"
            last_modified = page.get("lastModifiedDateTime") or page.get("lastModifiedTime", "unknown")
            md_content += f"> **Last Modified**: `{last_modified}`\n"
            md_content += f"> **Synced At**: `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`\n\n"
            md_content += "---\n\n"
            md_content += markdown + "\n"
            
            with open(dest_path, "w", encoding="utf-8") as f:
                f.write(md_content)
                
            print("✓")
            synced_pages.append({"title": title, "path": dest_path})
        except Exception as e:
            print(f"❌ FAILED: {e}")
            
    print(f"   Sync complete. {len(synced_pages)} pages processed.", flush=True)
    return synced_pages

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Microsoft OneNote Connector")
    parser.add_argument("--action", required=True, 
                        choices=["auth", "list-notebooks", "list-sections", "list-pages", "sync-journal"])
    parser.add_argument("--notebook-id", help="Notebook ID (for listing sections/pages)")
    parser.add_argument("--section-id", help="Section ID (for listing pages)")
    parser.add_argument("--dry-run", action="store_true", help="Perform a dry run without writing files")
    
    args = parser.parse_args()
    
    client = MicrosoftGraphClient()
    
    if args.action == "auth":
        client.device_flow_auth()
    elif args.action == "list-notebooks":
        try:
            resp = client.request(f"{client.graph_url}/me/onenote/notebooks")
            print("\nNotebooks:")
            for nb in resp["value"]:
                print(f"- {nb['displayName']} (ID: {nb['id']})")
        except Exception as e:
            print(f"Error listing notebooks: {e}. Did you run 'auth' first?")
    elif args.action == "list-sections":
        nb_id = args.notebook_id
        if not nb_id:
            print("Please specify --notebook-id")
            sys.exit(1)
        try:
            resp = client.request(f"{client.graph_url}/me/onenote/notebooks/{nb_id}/sections")
            print("\nSections:")
            for sec in resp["value"]:
                print(f"- {sec['displayName']} (ID: {sec['id']})")
        except Exception as e:
            print(f"Error listing sections: {e}")
    elif args.action == "list-pages":
        sec_id = args.section_id
        if not sec_id:
            print("Please specify --section-id")
            sys.exit(1)
        try:
            resp = client.request(f"{client.graph_url}/me/onenote/sections/{sec_id}/pages")
            print("\nPages:")
            for pg in resp["value"]:
                print(f"- {pg['title']} (ID: {pg['id']})")
        except Exception as e:
            print(f"Error listing pages: {e}")
    elif args.action == "sync-journal":
        sync_journal(client, dry_run=args.dry_run)

if __name__ == "__main__":
    main()
