import os
import sys
import json

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ONENOTE_SCRIPTS_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".agent", "skills", "onenote-connector", "scripts"))
sys.path.append(ONENOTE_SCRIPTS_DIR)

from onenote_client import MicrosoftGraphClient

def main():
    client = MicrosoftGraphClient()
    page_id = "0-7f557b90e2e18608045a15dbfaa661ea!1-4A7613E2B3A95908!183"
    
    print("Fetching page HTML...")
    try:
        content_html = client.request(
            f"{client.graph_url}/me/onenote/pages/{page_id}/content?includeIDs=true",
            is_json=False
        )
        print("Length of HTML:", len(content_html))
        print("HTML content preview:")
        print(content_html[:1500])
        
        # Save to file
        with open(os.path.join(SCRIPT_DIR, "page_test.html"), "w", encoding="utf-8") as f:
            f.write(content_html)
        print("Saved to page_test.html")
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    main()
