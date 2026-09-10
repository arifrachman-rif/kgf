import os
import io
import sys
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from googleapiclient.http import MediaIoBaseDownload

TOKEN_PATH = ".agent/skills/personal-drive-connector/token.json"

def download_file(file_id, output_path):
    creds = Credentials.from_authorized_user_file(TOKEN_PATH, ["https://www.googleapis.com/auth/drive"])
    service = build("drive", "v3", credentials=creds)
    
    request = service.files().get_media(fileId=file_id)
    fh = io.FileIO(output_path, "wb")
    downloader = MediaIoBaseDownload(fh, request)
    
    done = False
    while done is False:
        status, done = downloader.next_chunk()
        print(f"Download {int(status.progress() * 100)}%.")
    print(f"Downloaded to {output_path}")

if __name__ == "__main__":
    download_file("1_VsJJE6arwyuXPZhdbF6rDREyZ_QrVaD", "scratch/SHM_Enggal_1.pdf")
