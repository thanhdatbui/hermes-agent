# Triage Batch Alert O(1), Schema run_manifest.json & Khám Nghiệm Account Switcher XML (2026-09-23)

## 1. Triage Nhanh Batch Alert O(1) Không Quét Đĩa

Khi nhận cảnh báo diện rộng:
`🚨 [BATCH ALERT: LỖI HỆ THỐNG] PHÁT HIỆN LỖI LAN RỘNG - 【FARM KIBE - MÁY 1-80】`
`Quy mô batch: 80 máy | Thành công: X | Thất bại: Y`

### Bẫy quét đĩa & Timeout (Anti-Pattern):
- CẤM TUYỆT ĐỐI chạy `grep -rn` hoặc `search_files` trên thư mục code `python_runner` hay cây thư mục `D:/Taadaa` rộng lớn. Các lệnh này sẽ timeout >180s và tạo ra các tiến trình ngầm mồ côi (orphan background processes) gây lag máy.
- Mọi thông tin hiện trường của toàn bộ 80 máy trong Ca đã được runner tổng hợp sẵn tại file manifest duy nhất.

### Đường dẫn Artifact Ca Nuôi:
`D:/Taadaa/runtime/kibe/live/<YYYY-MM-DD>/<row-X-HHMMSS>/<YYYYMMDD-HHMMSS>/run_manifest.json`

### BẪY SCHEMA: `multi_machine_summary` là `list[dict]`, KHÔNG PHẢI `dict`:
- Trong `run_manifest.json`, `data["multi_machine_summary"]` là một danh sách 80 phần tử (tương ứng 80 máy).
- **CẤM gọi**: `data.get("multi_machine_summary", {}).get("machine_32")` -> Crash ngay lập tức với lỗi:
  `AttributeError: 'list' object has no attribute 'get'`
- **Cấu trúc mỗi phần tử**:
  ```python
  {
      "machine": 32,
      "account_row": 3,
      "serial": "ce0916094b33e73c03",
      "expected_username": "thanhlee327",
      "final_status": "manual-needed",  # "success", "blocked-proxy-vpn", "config-error", "fail", "failed"
      "swipes_completed": 0,
      "blocker_type": "script-blocker",
      "artifact_root": "D:\\Taadaa\\runtime\\kibe\\live\\...\\machines\\machine_32\\...",
      "stop_reason": "manual-needed:account-switcher-missing-expected: expected account not found in account switcher"
  }
  ```

### Script Triage Chuẩn O(1) (Chạy < 2 giây):
```python
import json
from collections import Counter

manifest_path = r"D:/Taadaa/runtime/kibe/live/2026-09-23/row-3-140057/20260923-140349/run_manifest.json"
with open(manifest_path, "r", encoding="utf-8") as f:
    data = json.load(f)

mms = data.get("multi_machine_summary", [])
status_counts = Counter(item.get("final_status") for item in mms)
print("Thống kê trạng thái:", status_counts)

print("\nDanh sách máy lỗi và nguyên nhân:")
for item in mms:
    st = item.get("final_status")
    if st != "success":
        print(f"M{item.get('machine'):02d}: status={st} | blocker={item.get('blocker_type')} | reason={item.get('stop_reason')}")
```

---

## 2. Khám Nghiệm Hiện Trường Account Switcher Sheet (Văng Nick vs Thiếu Slot)

Khi máy bị dừng với lỗi P0:
`manual-needed:account-switcher-missing-expected: expected account not found in account switcher`

### Bằng chứng xác thực tối cao: UI XML của Switcher Sheet
- Không đoán mò máy bị văng session hay chưa. Mở trực tiếp:
  `machines/machine_<N>/<run_id>/artifacts/device_<id>/account_<id>/feed-session-smoke/profile_preflight_switcher_1_guard/attempt_1/ui.xml`
- Parse XML lấy danh sách nick thực tế đang đăng nhập trên máy:
  ```python
  import xml.etree.ElementTree as ET
  tree = ET.parse(ui_xml_path)
  # Trên TikTok v47.x, username các nick trong sheet nằm ở node resource-id kết thúc bằng ':id/ndk'
  usernames = [node.attrib.get("text") for node in tree.findall(".//node") if node.attrib.get("resource-id", "").endswith(":id/ndk") and node.attrib.get("text")]
  print("Nick thực tế trên máy:", usernames)
  ```
- **So sánh đối soát với `taikhoan_run_safe.xlsx`**:
  - Nếu máy đang có 7/8 nick và nick báo lỗi là slot còn trống chưa từng đăng nhập -> **Đây là lỗi Nạp Thiếu Nick (Slot-Fill)**, không phải văng nick cũ.
  - Phân định rõ ràng trong báo cáo để tránh gây hoang mang về an toàn tài sản Farm.

---

## 3. Bẫy Device Lock Khi Fast Auto-Login Tự Cứu Từ Runner Cha

### Hiện tượng:
- Khi runner phát hiện thiếu nick trong switcher, nó kích hoạt hàm `_run_fast_targeted_login` gọi:
  `python D:\Taadaa\Tiktok_Reg\tiktok_login_v1.py <N> --email <target_id> --ss`
- `tiktok_login_v1.py` dùng `device_lock.py` để bảo vệ thiết bị.
- Nhưng tiến trình cha `run_tiktok.py` đang nắm active lock tại `C:\Users\Kibe\.codex\device-locks\machine_<N>.lock.json`.
- **Nếu thiếu `--allow-parent-lock`**:
  `tiktok_login_v1.py` phát hiện lock bị chiếm và lập tức crash với:
  `[device-lock] NEEDS_USER_DECISION: device lock active: ... project=tiktok-luot nuoi acc ...`
  `returncode = 2`.
- Hệ thống bị đẩy sang fallback reconcile chạy nặng nề và timeout 300s.

### Quy tắc bất biến:
Mọi sub-process công cụ con (như `tiktok_login_v1.py`, `reconcile_tiktok_accounts.py`) khi được gọi từ bên trong một runner cha đang sở hữu device lock BẮT BUỘC phải nhận cờ `--allow-parent-lock`.
