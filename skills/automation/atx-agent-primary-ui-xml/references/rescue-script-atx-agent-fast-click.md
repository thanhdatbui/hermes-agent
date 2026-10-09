# Cứu hộ giao diện Android qua atx-agent (JSON-RPC & HTTP Hierarchy)

## Bối cảnh & Nguyên nhân gốc
Trên các thiết bị Samsung Galaxy S7 (Android 7), khi điều hướng vào các màn hình phân cấp sâu (như Cài đặt & Quyền riêng tư của TikTok, Account Dropdown Switcher, Google Settings), việc gọi `adb shell uiautomator dump /sdcard/window_dump.xml` thường xuyên bị kernel Android OOM-kill (`Killed, EXIT=137`).
Nếu script cứu hộ hoặc worker subagent dùng lệnh này, subprocess sẽ bị treo ngậm timeout (lên tới 600s), làmCoordinator và User bị mất kết nối, tưởng nhầm hệ thống bị đơ.

## Quy chuẩn Script Cứu Hộ Nhanh qua atx-agent (Port 7912)

### 1. Port Forward
```python
import subprocess, urllib.request, json

ADB = r"C:\Program Files (x86)\xiaowei\tools\adb.exe"
SERIAL = "ce11160b1857760904"
PORT = 17953

# Forward port sang atx-agent đang chạy ngầm trên thiết bị
subprocess.run([ADB, "-s", SERIAL, "forward", f"tcp:{PORT}", "tcp:7912"], check=True)
```

### 2. Dump UI Hierarchy tươi (Zero OOM Crash)
```python
url = f"http://127.0.0.1:{PORT}/dump/hierarchy"
req = urllib.request.Request(url)
with urllib.request.urlopen(req, timeout=10) as resp:
    data = json.loads(resp.read().decode("utf-8"))
    xml_str = data.get("result", "")
    # Parse xml_str qua xml.etree.ElementTree bình thường
```

### 3. Click nhanh qua JSON-RPC (Không giật focus, không lag input)
```python
url = f"http://127.0.0.1:{PORT}/jsonrpc/0"
payload = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "click",
    "params": [540, 1662]  # [x, y]
}
req = urllib.request.Request(
    url,
    data=json.dumps(payload).encode("utf-8"),
    headers={"Content-Type": "application/json"}
)
with urllib.request.urlopen(req, timeout=5) as resp:
    res = json.loads(resp.read().decode("utf-8"))
```

## Invariant cho Coordinator Dispatch
Mọi prompt dispatch cho worker can thiệp UI hoặc xử lý cứu hộ thiết bị BẮT BUỘC inject điều khoản:
`CẤM TUYỆT ĐỐI gọi adb shell uiautomator dump (gây crash OOM 137). BẮT BUỘC dùng atx-agent port 7912.`

## Pitfall: Worker sao chép mã từ script cũ trong tools/ & Subprocess thiếu timeout (2026-09-23)
- **Hiện tượng:** Khi dispatch worker xử lý cứu hộ/logout máy (ví dụ Máy 53), worker tự ý đọc và sao chép mã từ các script cũ trong `D:/Taadaa/tools/` (`do_logout_account.py`, `clean_and_reconcile_farm_accounts.py`, `run_logout_all.py`).
- **Hậu quả:** 
  1. Các script cũ chứa lệnh `shell uiautomator dump` chưa dọn sạch $\rightarrow$ Android S7 OOM-kill (exit 137) khi mở sâu trang Cài đặt.
  2. Subprocess adb thiếu timeout $\rightarrow$ worker bị ngậm socket stall, treo cứng đúng 600s timeout, session hoàn toàn im ắng khiến user tưởng hệ thống bị đơ ("sao r treo lâu thế").
- **Kỷ luật bắt buộc:**
  1. Mọi script trong `tools/` phải được loại bỏ 100% tàn dư `uiautomator dump`, thay bằng `atx-agent` (port 7912 qua dynamic forward `tcp:17900+`).
  2. Mọi lệnh `subprocess.run` gọi ADB bắt buộc có `timeout=15` (hoặc bounded cap < 30s), cấm chạy không timeout.
  3. Coordinator khi dispatch worker cứu hộ thiết bị: cấp sẵn code snippet gọi `atx-agent` hoàn chỉnh, cấm worker tự probe và đọc các file legacy tool chưa thẩm định.

