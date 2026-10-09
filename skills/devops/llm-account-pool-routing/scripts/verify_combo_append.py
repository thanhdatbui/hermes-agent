#!/usr/bin/env python3
"""
verify_combo_append.py
Ad-hoc verification script cho việc append target vào combo trên OmniRoute.
Kiểm tra trực tiếp qua API live: http://127.0.0.1:20129/api/combos
và file: D:/Taadaa/GPM auto/config/oauth_pipeline_status.json
"""
import sys
import json
import urllib.request

def verify(target_email: str, expected_cid: str, combo_name: str = "ag-gemini-pool-3"):
    status_file = r"D:\Taadaa\GPM auto\config\oauth_pipeline_status.json"
    print(f"[VERIFY] Checking oauth_pipeline_status.json for {target_email}...")
    with open(status_file, "r", encoding="utf-8") as f:
        status_data = json.load(f)

    success_list = status_data.get("omniroute_success", [])
    assert target_email in success_list, f"Email {target_email} not in omniroute_success list!"
    print(f"✅ Email {target_email} confirmed in omniroute_success list!")

    print(f"[VERIFY] Querying live OmniRoute API (http://127.0.0.1:20129/api/combos) for combo '{combo_name}'...")
    req = urllib.request.Request("http://127.0.0.1:20129/api/combos")
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    combos = data.get("combos", [])
    target_combo = next((c for c in combos if c.get("name") == combo_name or c.get("id") == combo_name), None)
    assert target_combo is not None, f"Combo '{combo_name}' not found on OmniRoute!"

    models = target_combo.get("models", [])
    matched = [m for m in models if m.get("connectionId") == expected_cid]
    assert len(matched) > 0, f"Connection ID {expected_cid} not found in {combo_name} models!"
    print(f"✅ Connection ID {expected_cid} confirmed in '{combo_name}' (Total models: {len(models)})!")
    print("[VERIFY] All verification checks passed!")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python verify_combo_append.py <email> <expected_connection_id> [combo_name]")
        sys.exit(1)
    email = sys.argv[1]
    cid = sys.argv[2]
    cname = sys.argv[3] if len(sys.argv) > 3 else "ag-gemini-pool-3"
    verify(email, cid, cname)
