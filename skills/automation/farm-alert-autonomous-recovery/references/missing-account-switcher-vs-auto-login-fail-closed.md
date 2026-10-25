# Missing Account on Multi-Account Switcher: Triage & Auto-Login Recovery Flow

## 1. Hiện Tượng & Nguyên Tắc Vận Hành Cốt Lõi
Khi chạy batch Feed / Upload Hook, hệ thống phát cảnh báo P0:
```text
UploadHook: [ERROR] scripts.tiktok_workflow.state_machine: [ACCOUNT_SWITCHER_FAILED] select account failed: ACCOUNT_MISSING: expected account was not found.
```
- **Quy tắc bất biến của User:** Cứ thiếu acc (`ACCOUNT_MISSING` / `expected account was not found`) thì BẮT BUỘC hệ thống phải tự động kích hoạt flow `Thêm tài khoản` rồi TikTok Login bù vào slot còn thiếu (`recovery_handler = "tiktok_login"`).
- **CẤM TUYỆT ĐỐI:** Cấm viện cớ an toàn, cấm viện cớ "sợ lệch nhịp batch" hay "sợ văng phiên liên đới" để fail-closed dừng máy bắt người vận hành thao tác thủ công. Script login đã được thiết kế sẵn nhánh mở Switcher và tap `Thêm tài khoản`.

## 2. Kiến Trúc Kích Hoạt Tự Động (Đã Fix & Chuẩn Hóa)

### A. State Machine nhận diện thiếu acc (`scripts.tiktok_workflow.state_machine.py:5575`)
- Khi Switcher không tìm thấy target account (`err_msg` chứa `account_missing` hoặc `expected account was not found`):
  Hệ thống lập tức kích hoạt:
  ```python
  self.context.is_login_required = True
  self.context.is_no_account_login_required = True
  self.context.error = f"[LOGIN_RECOVERY_REQUIRED] {err_msg}."
  self.context.checkpoint["recovery_handler"] = "tiktok_login"
  ```
  -> `run_post.py` trả về exit code 4 với trạng thái `LOGIN_RECOVERY_REQUIRED`.

### B. Auto Login Handler qua Batch Runner (`run_tiktok_upload_batch.ps1`)
- Khi nhận `LOGIN_RECOVERY_REQUIRED`, batch runner khởi chạy `Start-LoginRecoveryRunner` để tự động chạy script login:
  ```powershell
  if (-not $ProfileSmoke -and $report -and $report.status -eq 'LOGIN_RECOVERY_REQUIRED' -and $runner.LoginRecoveryAttempt -eq 0) {
      $active[$key] = Start-LoginRecoveryRunner -Machine $runner.Machine
      continue
  }
  ```
- Khi login recovery exit code 0, runner đưa máy trở lại hàng đợi `$pending` để retry ca đăng video tự động một lần.

### C. Cấu hình lệnh Login Handler (`config-admin.yaml` & `config.example.yaml`)
- `login_recovery_command` được cấu hình để gọi trực tiếp script login tự động:
  ```yaml
  login_recovery_command:
    - "D:\\Taadaa\\python-envs\\automation\\Scripts\\python.exe"
    - "-X"
    - "utf8"
    - "D:\\Taadaa\\Tiktok_Reg\\tiktok_login_v1.py"
    - "{machine}"
    - "--all"
    - "--allow-parent-lock"
  ```
  **Lưu ý bắt buộc:**
  1. **Cờ `--all`:** BẮT BUỘC phải có `--all`. Nếu không có `--email` hay `--all`, `tiktok_login_v1.py` sẽ abort với lỗi: `STOPPED: Co nhieu account du info. Dung --email <mail|id> de chi ro account can login, hoac --all de chay tat ca account usable.` Với `--all`, script sẽ quét toàn bộ danh sách usable: nick nào đã có trong Switcher sẽ nhận diện `already_logged_in` và bỏ qua; chỉ nick thiếu mới bị đưa vào flow `tap_add_account` để login.
  2. **Python environment:** Trỏ đúng python của venv automation (`D:\Taadaa\python-envs\automation\Scripts\python.exe`) và cờ `-X utf8` để tránh lỗi encoding `cp1252` trên console Windows.
  3. **Host config (`taadaa_host.py`):** Trên cụm Admin (máy 201+), biến môi trường `TAADAA_HOST_CONFIG` phải là `D:/Taadaa/machine-config/admin.yaml` để script nạp đúng tracking workbook của Admin (`taikhoan_dat_v2_updated .xlsx`), không bị rơi về path của Kibe khiến 0 accounts được load.
  4. **Pitfall OneDrive dehydrated file (`RecallOnDataAccess` / `0x400000`):** Nếu `openpyxl` báo `TARGET_INVENTORY_READ_FAILED: OSError` (`[Errno 22] Invalid argument`), kiểm tra thuộc tính file workbook `taikhoan_run_safe.xlsx`. Nếu dính cờ `4199968` (RecallOnDataAccess/Offline), cần re-hydrate file bằng cách đọc stream byte và ghi đè lại nội bộ để file nằm thật sự trên ổ cứng.

## 3. Quy Trình Nạp Bù Tài Khoản Đúng Chuẩn (Actionable Reconcile Flow)
Để nạp nick còn thiếu vào slot trống của thiết bị mà không ảnh hưởng đến batch đang chạy:

1. **Sử dụng công cụ Reconcile chuyên dụng:**
   Script chuẩn: `D:/Taadaa/tiktok-log-in/scripts/reconcile_tiktok_accounts.py` (dùng engine `login_runner.account_reconcile` kết nối `Tiktok_Reg`).

2. **Cú pháp lệnh nạp bù 1 máy cụ thể (ví dụ M211 thiếu nick khanhcoi6114):**
   ```bash
   python D:/Taadaa/tiktok-log-in/scripts/reconcile_tiktok_accounts.py \
       --workbook "D:/OneDrive/TaadaaData/admin/taikhoan_run_safe.xlsx" \
       --machines 211 \
       --expected-username khanhcoi6114 \
       --adb-path "C:/Program Files (x86)/xiaowei/tools/adb.exe" \
       --login-project "D:/Taadaa/Tiktok_Reg" \
       --allow-live-reconcile
   ```

3. **Nguyên lý thực thi an toàn:**
   - Script tự động đối soát nick trong workbook với UI Switcher thực tế trên máy.
   - Bấm "Thêm tài khoản", thực hiện flow login có proxy xoay và giải mã IMAP OTP độc lập.
   - Sau khi login thành công, verify lại Switcher có đủ 8 slot trước khi nhả device lock.
