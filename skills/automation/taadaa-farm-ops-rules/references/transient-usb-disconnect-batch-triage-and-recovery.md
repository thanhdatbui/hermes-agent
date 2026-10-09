# Transient USB/ADB Disconnect Batch Alert Triage & Canary Recovery

## 1. Hiện Tượng & Signature Nhận Diện
- Nhận Batch Alert gom lỗi:
  ```text
  🚨 [BATCH ALERT: LỖI HỆ THỐNG] PHÁT HIỆN LỖI LAN RỘNG
  • Signature: proxy-vpn:device is offline or ADB/USB disconnected for <serial>: device offline or ADB/USB disconnected: adb.exe: device '<serial>' not found
  • Danh sách máy: M2, M3, M4... (10-20 máy thuộc cùng cụm hub)
  ```
- Thường xảy ra ở cụm hub USB công nghiệp khi có dao động nguồn/cáp uplink trong khoảnh khắc chạy batch, khiến một nhánh máy bị rớt kết nối ADB tạm thời.

---

## 2. Quy Trình Triage O(1) Chuẩn Cho Coordinator

### Bước 1: Kiểm tra PnP Kernel USB & Lệnh Canary
1. **Kiểm tra tầng PnP USB Host (xem có sập nguồn hub cứng không):**
   ```powershell
   powershell.exe -NoProfile -Command '
   Get-PnpDevice -PresentOnly | Where-Object { 
       $_.FriendlyName -like "*Descriptor Request Failed*" -or 
       $_.FriendlyName -like "*Port Reset Failed*" 
   } | Measure-Object | Select-Object -ExpandProperty Count
   '
   ```
   - Nếu $\ge 10$ lỗi: Nguồn hub bị mất hẳn điện hoặc cáp USB uplink tuột hoàn toàn. Cần can thiệp vật lý tại chỗ.
   - Nếu $= 0$ hoặc $1$: Phần cứng USB Host bình thường, khả năng cao là lỗi transient đã hồi phục.

2. **Chạy Canary inspect trên máy đại diện (ví dụ M2):**
   ```bash
   python D:/Taadaa/tools/inspect_machine.py M2
   ```

### Bước 2: Mapping Máy M<id> -> ADB Serial (O(1), Cấm Scan Đĩa)
Thay vì grep scan toàn đĩa, dùng trực tiếp helper có sẵn của repo:
```python
import subprocess, sys
sys.path.insert(0, r'D:/Taadaa/tiktok-luot nuoi acc/python_runner')
from core.feed_session_workbook import select_feed_session_accounts

error_machines = [2, 3, 4, 5, 6, 8, 9, 10, 12, 13, 14, 15, 17, 19, 30]
res = select_feed_session_accounts(
    r'D:/OneDrive/TaadaaData/kibe/taikhoan_run_safe.xlsx',
    machines=error_machines,
    row_index=1
)

adb_path = r'C:\Program Files (x86)\xiaowei\tools\adb.exe'
out = subprocess.check_output([adb_path, 'devices'], text=True)
online_serials = {line.split('\t')[0].strip() for line in out.splitlines() if '\tdevice' in line}

for acc in res.accounts:
    status = 'ONLINE' if acc.serial in online_serials else 'OFFLINE'
    print(f'M{acc.machine} ({acc.serial}): {status}')
```

### Bước 3: Lấy Bằng Chứng Hiện Trường Canary
1. Kiểm tra trạng thái máy canary:
   ```bash
   "C:\Program Files (x86)\xiaowei\tools\adb.exe" -s <serial> get-state
   "C:\Program Files (x86)\xiaowei\tools\adb.exe" -s <serial> shell "dumpsys window | grep -E 'mCurrentFocus|mFocusedApp'"
   ```
2. Chụp ảnh màn hình lưu cache và gắn tag `MEDIA:` để gửi Telegram:
   ```bash
   "C:\Program Files (x86)\xiaowei\tools\adb.exe" -s <serial> exec-out screencap -p > "C:\Users\Kibe\AppData\Local\hermes\cache\canary_m<id>.png"
   ```

---

## 3. Quyết Định Điều Phối & Mở Khóa Fleet
1. **Nếu phần lớn máy đã tự ONLINE trở lại (Transient Disconnect):**
   - Báo cáo rõ số lượng máy đã tự phục hồi (ví dụ 14/15 máy online).
   - Tách riêng các máy còn OFFLINE thật (ví dụ M30).
   - Mở khóa vận hành cho các máy online.
   - Thêm các máy còn offline vào danh sách loại trừ (`excluded_machines` trong `scheduler-control.json`) để không làm nghẽn batch tiếp theo, đồng thời báo người vận hành cắm lại cáp vật lý riêng cho máy đó.
2. **Nếu toàn bộ nhánh máy vẫn OFFLINE:**
   - Báo cáo lỗi phần cứng cụm Hub, không cố retry script hay khởi động lại ADB vô ích.

---

## 4. Pitfall: Socket ADB Daemon Contention Do Worker Con Spam Đồng Thời
- **Hiện tượng:** Khi chạy multi-machine với hàng chục worker song song, nhiều worker cùng lúc gọi `adb.list_devices()` trong vòng vài chục mili-giây, khiến daemon trả về danh sách thiếu tạm thời.
- **Biện pháp:** Trong `multi_machine_feed_session.py`, hàm `_validate_child_adb` phải có retry tối thiểu `ADB_ONLINE_ATTEMPTS = 5` kèm jitter/backoff (`time.sleep(1.0 + 0.5 * _attempt)`) thay vì retry 2 lần cộc lốc khiến máy online bị rớt nhầm sang `config-error`.

