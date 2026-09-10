import os
import io
import sys
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import pandas as pd

def main():
    SCRIPT_DIR = os.path.abspath(os.path.join('.agent', 'skills', 'work-drive-connector'))
    TOKEN_FILE = os.path.join(SCRIPT_DIR, 'token.json')
    
    if not os.path.exists(TOKEN_FILE):
        print(f"Token not found at {TOKEN_FILE}")
        return

    creds = Credentials.from_authorized_user_file(TOKEN_FILE, ['https://www.googleapis.com/auth/drive'])
    service = build('drive', 'v3', credentials=creds)

    file_id = "18nz_6tPoNoxqrhkJr82CYYcY83rndWBS"
    print(f"Downloading file ID: {file_id}")

    request = service.files().get_media(fileId=file_id)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while done is False:
        status, done = downloader.next_chunk()
        print(f"Download {int(status.progress() * 100)}%.")

    with open('budget.xlsx', 'wb') as f:
        f.write(fh.getvalue())
        
    print("Download complete. Reading with pandas...")
    
    # Read all sheets
    xls = pd.ExcelFile('budget.xlsx')
    print(f"Found sheets: {xls.sheet_names}")
    
    for sheet_name in xls.sheet_names:
        df = pd.read_excel('budget.xlsx', sheet_name=sheet_name)
        # Search for PTKGF or KGF
        # Let's save each sheet to a CSV to easily inspect if we need to
        csv_filename = f"budget_{sheet_name.replace(' ', '_')}.csv"
        df.to_csv(csv_filename, index=False)
        print(f"Saved {csv_filename}")
        
if __name__ == "__main__":
    main()
