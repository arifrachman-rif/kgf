import os
import sys
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

def main():
    SCRIPT_DIR = os.path.abspath(os.path.join('.agent', 'skills', 'work-drive-connector'))
    TOKEN_FILE = os.path.join(SCRIPT_DIR, 'token.json')
    
    if not os.path.exists(TOKEN_FILE):
        print(f"Token not found at {TOKEN_FILE}")
        return

    creds = Credentials.from_authorized_user_file(TOKEN_FILE)
    service = build('sheets', 'v4', credentials=creds)
    spreadsheet_id = "18nz_6tPoNoxqrhkJr82CYYcY83rndWBS"

    # Get sheet metadata to find the name of gid=570653277
    try:
        sheet_metadata = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    except Exception as e:
        print(f"Failed to access spreadsheet: {e}")
        return

    sheets = sheet_metadata.get('sheets', '')
    target_sheet_name = None
    
    print("Sheets available:")
    for sheet in sheets:
        prop = sheet.get('properties', {})
        print(f" - {prop.get('title')} (gid={prop.get('sheetId')})")
        if str(prop.get('sheetId')) == "570653277":
            target_sheet_name = prop.get('title')
            
    if not target_sheet_name:
        target_sheet_name = sheets[0].get('properties', {}).get('title')
        print(f"GID not found. Defaulting to {target_sheet_name}")

    print(f"\nFetching data from: {target_sheet_name}")
    result = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id, range=target_sheet_name).execute()
    
    rows = result.get('values', [])
    print(f"Found {len(rows)} rows.")
    
    import csv
    with open('sheet_data.csv', 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        for row in rows:
            writer.writerow(row)
            
    print("Data saved to sheet_data.csv")

if __name__ == "__main__":
    main()
