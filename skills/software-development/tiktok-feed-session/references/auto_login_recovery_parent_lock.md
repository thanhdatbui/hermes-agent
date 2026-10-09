# Auto-Login Recovery & Batch Alert Triage trong TikTok Feed Session

## 1. Fast Targeted Login Recovery & Cờ `--allow-parent-lock`

### Bối cảnh & Cơ chế
Khi `feed_swipe_smoke.py` thực hiện profile preflight và phát hiện tài khoản dự kiến không có trong danh sách Account Switcher (`manual-needed:account-switcher-missing-expected`), runner kích hoạt quy trình tự phục hồi nhanh (Fast Auto-Login):
- Lệnh: `python D:\Taadaa\Tiktok_Reg\tiktok_login_v1.py <machine_id> --email <expected_id> --ss --allow-parent-lock`

### Pitfall chí mạng: Xung đột Device Lock giữa Parent Runner và Fast Login
- `run_tiktok.py` (tiến trình cha) khi chạy chế độ multi-machine đã acquire device lock tại `C:\Users\Kibe\.codex\device-locks\machine_<N>.lock.json`.
- `tiktok_login_v1.py` (tiến trình con) cũng dùng thư viện `device_lock.py` để acquire lock trước khi thao tác ADB.
- **Nếu thiếu cờ `--allow-parent-lock`**:
  `tiktok_login_v1.py` sẽ raise `DeviceLockNeedsUserDecision` với thông báo:
  `[device-lock] NEEDS_USER_DECISION: device lock active: path=... pid=... host=... project=tiktok-luot nuoi acc machine=<N> ... command=run_tiktok.py`
  và lập tức exit với `returncode = 2`.
- Hậu quả: Fast auto-login thất bại trong 6 giây, hệ thống fallback sang `reconcile_tiktok_accounts.py` chạy nặng nề và dễ dính timeout 300s, dẫn đến máy bị gán nhãn `manual-needed` và bỏ dở ca nuôi.
- **Quy tắc bất biến**: Mọi invocation gọi sang `tiktok_login_v1.py` từ bên trong runner đang giữ device lock BẮT BUỘC phải truyền cờ `--allow-parent-lock`.

---

## 2. Cấu trúc Schema `run_manifest.json` để Triage Batch Alert O(1)

Đường dẫn manifest:
`D:/Taadaa/runtime/kibe/live/<YYYY-MM-DD>/<row-X-HHMMSS>/<YYYYMMDD-HHMMSS>/run_manifest.json`

### Lưu ý cấu trúc dữ liệu quan trọng:
- Trường `multi_machine_summary` là một **`list[dict]`**, KHÔNG PHẢI `dict`.
- CẤM gọi `data.get("multi_machine_summary", {}).get(...)` -> sẽ crash `AttributeError: 'list' object has no attribute 'get'`.
- Mỗi phần tử trong danh sách tương ứng với 1 máy:
  ```python
  {
      "machine": 32,
      "account_row": 3,
      "serial": "ce0916094b33e73c03",
      "expected_username": "thanhlee327",
      "final_status": "manual-needed",  # "success" | "blocked-proxy-vpn" | "config-error" | "fail" | "failed"
      "swipes_completed": 0,
      "blocker_type": "script-blocker",
      "artifact_root": "D:\\Taadaa\\runtime\\kibe\\live\\...\\machines\\machine_32\\...",
      "stop_reason": "manual-needed:account-switcher-missing-expected: expected account not found in account switcher"
  }
  ```

### Snippet Python chuẩn trích xuất nhanh 18/80 máy lỗi không tốn token:
```python
import json
from collections import Counter

manifest_path = r"D:/Taadaa/runtime/kibe/live/.../run_manifest.json"
with open(manifest_path, "r", encoding="utf-8") as f:
    data = json.load(f)

mms = data.get("multi_machine_summary", [])
status_counts = Counter(item.get("final_status") for item in mms)
print("Phân bố trạng thái:", status_counts)

for item in mms:
    if item.get("final_status") != "success":
        print(f"M{item.get('machine'):02d}: {item.get('final_status')} | {item.get('blocker_type')} | {item.get('stop_reason')}")
```

---

## 3. Cách đọc UI XML của Account Switcher Sheet

Khi máy báo `account-switcher-missing-expected`:
- Mở file:
  `machines/machine_<N>/<run_id>/artifacts/device_<id>/account_<id>/feed-session-smoke/profile_preflight_switcher_1_guard/attempt_1/ui.xml`
- Quét nhanh các node:
  ```python
  import xml.etree.ElementTree as ET
  tree = ET.parse(xml_path)
  accounts = [n.attrib.get("text") for n in tree.findall(".//node") if n.attrib.get("resource-id", "").endswith(":id/ndk") and n.attrib.get("text")]
  print("Danh sách nick thực tế trong Switcher:", accounts)
  ```
- So khớp với file `taikhoan_run_safe.xlsx` để biết ngay thiết bị đang thiếu slot nào, tránh đoán mò.
