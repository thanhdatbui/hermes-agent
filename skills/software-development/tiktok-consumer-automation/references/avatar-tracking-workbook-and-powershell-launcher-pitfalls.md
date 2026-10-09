# Avatar Tracking, Workbook Atomic Updates & PowerShell Launcher Pitfalls

## 1. Scope & Background
Khi triển khai Avatar upload tracking tách rời khỏi video upload (`run_tiktok_upload_avatar.ps1` và `scripts/tiktok_workflow/account_source.py`), có 3 cạm bẫy quan trọng về Python scope, PowerShell CLI quoting và farm operational invariants.

---

## 2. Pitfall: Module-Level vs Local Scope cho `atomic_workbook_update`
Trong `account_source.py`, phương thức `increment_posted_count()` thường import hoặc khai báo hàm `atomic_workbook_update` cục bộ bên trong hàm.
- **Vấn đề**: Khi viết thêm phương thức mới `update_avatar_status(self, status: str = "OK")` gọi `atomic_workbook_update(workbook_path, ...)`, Python sẽ ném lỗi:
  ```python
  NameError: name 'atomic_workbook_update' is not defined
  ```
- **Khắc phục**: Luôn đảm bảo `atomic_workbook_update` được import tại module level (đầu file):
  ```python
  from automation_core.workbook import atomic_workbook_update
  ```
  Package `automation_core` đã được cài đặt trong virtual environment (`D:\Taadaa\automation-core\src`). Không dựa vào local import bên trong hàm khác.

---

## 3. Pitfall: PowerShell Here-String & `python -c` Argument Mangling
Khi launcher PowerShell (`.ps1`) gọi một đoạn mã Python nội suy để quét danh sách máy chưa có Avatar (`$ForceAvatarMachineList` fallback):
- **Cạm bẫy 1: CommandLineToArgvW Quote Stripping**:
  Nếu chạy qua `& python -c $pyScript`:
  Windows CRT argument parsing (`CommandLineToArgvW`) sẽ bóc tách các dấu ngoặc kép hoặc dấu nháy bên trong `$pyScript`, làm các chuỗi đường dẫn như `wb_path = r"D:\OneDrive\..."` bị biến thành `wb_path = rD:\OneDrive\...` gây `SyntaxError: invalid syntax`.
  **Giải pháp chuẩn**: Luôn truyền qua stdin:
  ```powershell
  $resolvedList = $pyScript | & python
  ```
  Cách này bảo toàn 100% cú pháp, dấu nháy kép/đơn và multiline string.

- **Cạm bẫy 2: Escape ký tự `$` trong script PowerShell**:
  Trong prompt hoặc tài liệu markdown, các biến thường bị escape thành `` `$var `` hoặc `\$var`. Nếu đưa nguyên si vào file `.ps1`:
  ```powershell
  `$pyScript = @" ... "@
  ```
  PowerShell sẽ hiểu `` `$pyScript `` là tên lệnh gọi thực thi và ném lỗi:
  ```
  CommandNotFoundException: The term '$pyScript' is not recognized as the name of a cmdlet...
  ```
  File `.ps1` thực tế phải dùng `$pyScript = @" ... "@` chuẩn.

---

## 4. Farm Rules & Workbook Avatar Status Contract
- **Không bỏ qua Máy 38**: Trong các đợt migration hoặc gán cờ Avatar trên Tik1..Tik6, Máy 38 là máy hoạt động bình thường, tuyệt đối không được skip hoặc loại trừ.
- **Avatar Status Invariants**:
  - Tik1..Tik3: Hàng có `Video Đã Đăng >= 1` được đánh dấu Avatar = `"OK"`.
  - Tik4: Hàng có `Video Đã Đăng >= 1` HOẶC `Máy == 36` được đánh dấu Avatar = `"OK"`.
  - Tik5, Tik6: Giữ nguyên (None/trống) cho các tài khoản mới chờ upload.
- **Idempotency Ledger**:
  Sau khi upload avatar thành công, ngoài ghi nhận vào workbook, state machine ghi log append-only vào `runtime_root/idempotency/avatar-ledger.jsonl`:
  ```json
  {"timestamp": "...", "machine": "...", "device_id": "...", "account": "...", "folder": "...", "status": "VERIFIED_SUCCESS"}
  ```
