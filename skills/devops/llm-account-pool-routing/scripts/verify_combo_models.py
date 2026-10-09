#!/usr/bin/env python3
"""
Verify that a specific Connection ID is present in an OmniRoute combo's models list.
Usage: python verify_combo_models.py <connection_id> [combo_name_or_id] [omni_url]
"""
import sys
import json
import urllib.request

def main():
    if len(sys.argv) < 2:
        print("Usage: verify_combo_models.py <connection_id> [combo_name_or_id] [omni_url]")
        sys.exit(1)

    cid = sys.argv[1].strip()
    combo_target = sys.argv[2].strip() if len(sys.argv) > 2 else "ag-gemini-pool-3"
    base_url = sys.argv[3].rstrip("/") if len(sys.argv) > 3 else "http://127.0.0.1:20129"

    url = f"{base_url}/api/combos"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "OmniComboVerifier/1.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        combos = data.get("combos", []) if isinstance(data, dict) else data
        combo = next((c for c in combos if isinstance(c, dict) and (c.get("name") == combo_target or c.get("id") == combo_target)), None)

        if not combo:
            print(f"FAIL: Combo '{combo_target}' not found in {len(combos)} combos.")
            sys.exit(1)

        # NOTE: OmniRoute combo schema stores member connections under 'models' list,
        # with attribute 'connectionId' (NOT 'targets' / 'connection_id').
        models = combo.get("models", [])
        found = any(isinstance(m, dict) and m.get("connectionId") == cid for m in models)

        if found:
            print(f"VERIFICATION SUCCESS: connectionId '{cid}' is present in models of combo '{combo_target}' (total models: {len(models)}).")
            sys.exit(0)
        else:
            print(f"FAIL: connectionId '{cid}' not found in models of combo '{combo_target}' (total models: {len(models)}).")
            sys.exit(1)
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
