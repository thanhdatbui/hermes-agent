# Stale Device Lock & Account Switcher Placeholder Matching

## 1. Stale Device Lock Resolution (Cặp lock: machine_N & serial_<serial>)

### Cơ chế Lock Protocol v2:
- Khi runner chạy, nó tạo 2 lock files trong `C:\Users\Kibe\.codex\device-locks\`:
  - `machine_<N>.lock.json` (theo số thứ tự máy, ví dụ: `machine_5.lock.json`)
  - `serial_<serial>.lock.json` (theo serial thiết bị, ví dụ: `serial_9885e64b4a434a3037.lock.json`)
- Khi tiến trình kết thúc với trạng thái `manual-needed` hoặc `blocked`, file lock được cập nhật `status: blocked`, `owner_active: false`.

### Quy trình kiểm tra và dọn stale lock:
1. **Kiểm tra tiến trình sở hữu PID còn sống không:**
   ```powershell
   Get-Process -Id <PID> -ErrorAction SilentlyContinue
   ```
   hoặc Python:
   ```python
   import psutil
   psutil.pid_exists(<PID>)
   ```
2. **Xóa CẢ HAI lock file nếu PID đã chết (stale lock):**
   - Không được chỉ xóa `machine_<N>.lock.json` mà bỏ quên `serial_<serial>.lock.json`.
   - Nếu sót file serial lock, runner sẽ tiếp tục báo thiết bị bị lock bởi process cũ.
   ```python
   import os
   for name in [f'machine_{N}.lock.json', f'serial_{SERIAL}.lock.json']:
       p = os.path.join(r'C:\Users\Kibe\.codex\device-locks', name)
       if os.path.exists(p):
           os.remove(p)
   ```

---

## 2. Account Switcher Placeholder Matching (`user\d+` vs Target Username)

### Hiện tượng:
- Runner dừng phiên với lỗi:
  `manual-needed:account-switcher-missing-expected: expected account not found in account switcher`
- Mặc dù account switcher đã mở thành công và trong danh sách có tài khoản dạng placeholder như `user1196792370966`.

### Nguyên nhân:
- Tài khoản TikTok mới reg hoặc chưa set handle thường hiển thị trong Switcher dưới dạng `user\d+` (ví dụ `user1196792370966`), trong khi workbook hoặc target yêu cầu username thật (ví dụ `stevemgjqec`).
- Nếu logic `try_user_placeholder_account` bị revert/thiếu trong `feed_swipe_smoke.py`:
  - `_find_account_switch_option(popup_xml, expected)` chỉ so khớp chuỗi `expected` với text/content-desc trong switcher.
  - Không tìm thấy exact match -> runner coi như thiếu tài khoản và dismiss switcher.

### Quy chuẩn xử lý:
- Trong `_find_account_switch_option` hoặc bước fallback của switcher:
  - Khi không tìm thấy exact account, kiểm tra xem có candidate dạng `^user\d+$` hay không.
  - Nếu có, tap candidate `user\d+` (`try_user_placeholder_account`), switch sang tài khoản đó rồi mới verify username/display name trên màn hình Profile.
  - Cẩn trọng khi rebase hoặc revert code giữa các máy (ví dụ Máy 40 dọn code adb keyevent không được xóa nhầm logic placeholder matcher của switcher).

---

## 3. PowerShell Variable Expansion Pitfall trong Runner Script

- Trong PowerShell script (như `run-feed-session.ps1`), viết:
  ```powershell
  Write-Warning "[PRE-FLIGHT] Loi khi kiem tra lock may $m: $($_.Exception.Message)"
  ```
  sẽ bị PowerShell parser hiểu nhầm `$m:` là drive/scope variable (`InvalidVariableReferenceWithDrive`).
- **Khắc phục:** Luôn bọc `${m}:` hoặc `$($m):` khi có dấu hai chấm ngay sau tên biến:
  ```powershell
  Write-Warning "[PRE-FLIGHT] Loi khi kiem tra lock may ${m}: $($_.Exception.Message)"
  ```
