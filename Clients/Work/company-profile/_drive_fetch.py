"""List and download the contents of a Drive folder by ID.

The stock connectors only search by name, so this reuses their credentials to do
a parents-based listing. Tries each of the three accounts until one can see the
folder, since a shared folder may sit on any of them.

  python Clients/Work/company-profile/_drive_fetch.py list   <folderId>
  python Clients/Work/company-profile/_drive_fetch.py fetch  <folderId> <destDir>
"""
import sys, os, io, importlib.util

SKILLS = {
    "work":      ".agent/skills/work-drive-connector/gdrive_manager.py",
    "personal":  ".agent/skills/personal-drive-connector/gdrive_manager.py",
    "secondary": ".agent/skills/secondary-drive-connector/gdrive_manager.py",
}


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def service_for(account):
    from googleapiclient.discovery import build
    mod = load(SKILLS[account], "gdm_" + account)
    creds = mod.authenticate()
    if not creds:
        return None
    return build("drive", "v3", credentials=creds)


def children(svc, folder_id):
    out, token = [], None
    while True:
        r = svc.files().list(
            q=f"'{folder_id}' in parents and trashed = false",
            pageSize=200, pageToken=token,
            fields="nextPageToken, files(id, name, mimeType, size, imageMediaMetadata)",
            supportsAllDrives=True, includeItemsFromAllDrives=True,
        ).execute()
        out += r.get("files", [])
        token = r.get("nextPageToken")
        if not token:
            break
    return out


def find_account(folder_id):
    """Return (account, service, folder metadata) for whichever account can see it."""
    for acct in SKILLS:
        try:
            svc = service_for(acct)
            if not svc:
                continue
            meta = svc.files().get(fileId=folder_id, fields="id, name, mimeType",
                                   supportsAllDrives=True).execute()
            return acct, svc, meta
        except Exception as e:
            print(f"  {acct}: {type(e).__name__}", file=sys.stderr)
    return None, None, None


def main():
    action = sys.argv[1]
    folder_id = sys.argv[2]

    acct, svc, meta = find_account(folder_id)
    if not svc:
        print("No account could open that folder.")
        return 1
    print(f"account : {acct}")
    print(f"folder  : {meta['name']}")

    files = sorted(children(svc, folder_id), key=lambda f: f["name"])
    print(f"items   : {len(files)}\n")
    for f in files:
        dims = ""
        im = f.get("imageMediaMetadata") or {}
        if im.get("width"):
            dims = f"  {im['width']}x{im['height']}"
        mb = int(f.get("size", 0)) / 1048576 if f.get("size") else 0
        print(f"  {f['name']:<48} {f['mimeType'].split('/')[-1]:<10} {mb:5.1f}MB{dims}")

    if action == "fetch":
        from googleapiclient.http import MediaIoBaseDownload
        dest = sys.argv[3]
        os.makedirs(dest, exist_ok=True)
        print("")
        for f in files:
            if not f["mimeType"].startswith("image/"):
                continue
            out = os.path.join(dest, f["name"])
            req = svc.files().get_media(fileId=f["id"])
            with io.FileIO(out, "wb") as fh:
                dl = MediaIoBaseDownload(fh, req)
                done = False
                while not done:
                    _, done = dl.next_chunk()
            print("downloaded", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
