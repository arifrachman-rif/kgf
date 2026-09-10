import urllib.request
import urllib.parse
import json

def test_device_flow(client_id, scopes):
    print(f"Testing client_id: {client_id} with scopes: {scopes}")
    url = "https://login.microsoftonline.com/common/oauth2/v2.0/devicecode"
    payload = {
        "client_id": client_id,
        "scope": scopes
    }
    req_data = urllib.parse.urlencode(payload).encode("utf-8")
    req = urllib.request.Request(url, headers={"Content-Type": "application/x-www-form-urlencoded"}, data=req_data, method="POST")
    try:
        with urllib.request.urlopen(req) as r:
            resp = json.loads(r.read().decode("utf-8"))
            print("SUCCESS starting device flow!")
            print(resp)
            return resp
    except Exception as e:
        print(f"FAILED: {e}")
        if hasattr(e, 'read'):
            print(e.read().decode("utf-8"))
        return None

# Test rclone client ID
test_device_flow("b15694e9-56ca-47c1-ae45-b0d87fa541d2", "Notes.Read Notes.ReadWrite Files.Read Files.ReadWrite offline_access")
