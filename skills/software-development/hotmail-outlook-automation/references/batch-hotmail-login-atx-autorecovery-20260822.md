# Batch Hotmail Login with In-Loop ATX Auto-Recovery

## Problem Statement
During farm-wide batch Hotmail/Outlook login across dozens of Samsung S7 devices, the `atx-agent` daemon or its UiAutomator stub (`com.github.uiautomator`) frequently crashes or becomes wedged (returning `RemoteDisconnected` or `HTTP Error 502: Bad Gateway` on `/jsonrpc/0` `dumpWindowHierarchy`).
Previously, runners without in-loop ATX recovery would mark the machine as `UNKNOWN_SCREEN` and skip to the next device, leaving accounts unconsumed.

## Solution & In-Loop Auto-Recovery Pattern

Import and use `reset_atx_agent` from `automation_core.persistent_ui` inside the UI dump helper:

```python
from automation_core.adb import AdbClient
from automation_core.persistent_ui import reset_atx_agent

def get_ui_xml_with_auto_recovery(adb_path: str, serial: str, port: int = 7912) -> str:
    url = f"http://127.0.0.1:{port}/jsonrpc/0"
    payload = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "dumpWindowHierarchy", "params": [True]}).encode()
    
    # 1. Try 2 times normally
    for _ in range(2):
        try:
            req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=6) as response:
                data = json.loads(response.read().decode())
                xml = data.get("result", "")
                if xml and "<hierarchy" in xml:
                    return xml
        except Exception:
            pass
        time.sleep(0.5)
        
    # 2. Hard reset ATX daemon + stub using standard farm helper
    client = AdbClient(adb_path=adb_path, serial=serial)
    reset_atx_agent(client, timeout=15)
    time.sleep(1.5)
    subprocess.run([adb_path, "-s", serial, "forward", f"tcp:{port}", "tcp:7912"], capture_output=True)
    
    # 3. Retry dump after reset
    try:
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
            return data.get("result", "")
    except Exception as e:
        return ""
```

## `reset_atx_agent` Mechanism in `automation_core`
1. `am force-stop com.github.uiautomator` (stops stub)
2. `pkill -9 -f atx-agent` & `pkill -9 -f uiautomator` (kills wedged processes)
3. `/data/local/tmp/atx-agent server -d` (restarts daemon)
4. `monkey -p com.github.uiautomator 1` (wakes up UiAutomator stub on Android 7/8)

## Verified Results (2026-08-22)
- Applied to `run_batch_login_xml.py` in `D:\Taadaa\Hotmail\scripts\`.
- Successfully recovered dead ATX on Machines 73, 36, 16, 2, 26, 60.
- Reached 100% completion: 27/27 Hotmail accounts loaded and verified across 27 farm devices.
