# Tự động phục hồi ATX-Agent (Auto-Recovery) trên Farm Android

Khi chạy các batch runner qua nhiều thiết bị (như batch login Hotmail, TikTok Nuôi acc, Reconcile), daemon `atx-agent` hoặc stub `com.github.uiautomator` có thể bị Android hệ thống giải phóng bộ nhớ hoặc treo socket, dẫn đến lỗi:
- `HTTP Error 502: Bad Gateway`
- `http.client.RemoteDisconnected: Remote end closed connection without response`
- `dumpWindowHierarchy` timeout / crash

### 1. Chuẩn phục hồi trong code (`automation_core.persistent_ui`)

Sử dụng hàm:
```python
from automation_core.persistent_ui import reset_atx_agent
from automation_core.adb import AdbClient

client = AdbClient(adb_path=adb_path, serial=serial)
reset_atx_agent(client, timeout=15)
```

Quy trình 4 bước được đóng gói bên trong:
1. `am force-stop` các stub packages (`com.github.uiautomator`).
2. `pkill -9 -f atx-agent` và `pkill -9 -f uiautomator` để dọn sạch socket/process kẹt.
3. Chạy daemon nền: `/data/local/tmp/atx-agent server -d`.
4. Relaunch stub bằng lệnh monkey: `monkey -p com.github.uiautomator 1` (chuẩn Android 7/8).

### 2. Mẫu tích hợp tự động trong `get_ui_xml` của Consumer Runner

```python
def get_ui_xml_with_auto_recovery(adb_path: str, serial: str, port: int = 7912) -> str:
    url = f"http://127.0.0.1:{port}/jsonrpc/0"
    payload = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "dumpWindowHierarchy", "params": [True]}).encode()
    
    # Thử 2 lần bình thường
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
        
    # Tự động hard reset ATX nếu fail
    client = AdbClient(adb_path=adb_path, serial=serial)
    reset_atx_agent(client, timeout=15)
    time.sleep(1.5)
    subprocess.run([adb_path, "-s", serial, "forward", f"tcp:{port}", "tcp:7912"], capture_output=True)
    
    # Retry lấy XML sau reset
    try:
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
            return data.get("result", "")
    except Exception as e:
        return ""
```
