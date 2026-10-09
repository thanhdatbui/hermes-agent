# Windows SSH PowerShell EncodedCommand & 2FA Audit Log Backfill Protocol

## 1. Vấn đề cốt lõi khi điều phối SSH sang máy Windows khác (Admin Farm)
Khi điều phối chạy batch script từ controller sang host Windows từ xa qua OpenSSH:
- **Lỗi Encoding Unicode (`Tài Khoản`)**: PowerShell mặc định trên host Windows dùng console code page (cp1252/cp936), khi nhận tham số tiếng Việt có dấu qua SSH đối số dòng lệnh sẽ ném `UnicodeEncodeError: 'charmap' codec can't encode character '\u1ea3'`.
- **Lỗi vỡ đối số có khoảng trắng trong đường dẫn**: Đường dẫn như `'D:/OneDrive/TaadaaData/admin/taikhoan_dat_v2_updated .xlsx'` khi truyền qua `ssh host powershell -Command "..."` thường bị shell quote stripping, khiến Python runner báo lỗi `unrecognized arguments: .xlsx`.

### Chuẩn hóa giải pháp: PowerShell Base64 EncodedCommand
Tuyệt đối không dùng chuỗi thô lồng nhau qua SSH. Bắt buộc đóng gói toàn bộ script PowerShell thành UTF-16LE và Base64 encode:

```python
import base64
import subprocess

ps_admin_script = (
    "$env:PYTHONIOENCODING = 'utf-8'\n"
    "$env:PYTHONUTF8 = '1'\n"
    "Set-Location 'D:/Taadaa/tiktok-add-bao-mat-f2a'\n"
    "$wb = 'D:\\OneDrive\\TaadaaData\\admin\\taikhoan_dat_v2_updated .xlsx'\n"
    "& 'D:\\Taadaa\\python-envs\\automation\\Scripts\\python.exe' python_runner/run_batch_live_2fa.py "
    "--workbook-path $wb --workbook-sheet 'Tài Khoản' --max-workers 40 --live\n"
)
b64_ps = base64.b64encode(ps_admin_script.encode("utf-16le")).decode("ascii")
cmd_admin = [
    "ssh", "-o", "ConnectTimeout=10", "admin-farm",
    f"powershell -NoProfile -EncodedCommand {b64_ps}"
]
proc = subprocess.run(cmd_admin, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=5400)
```

---

## 2. Quy trình Cứu hộ & Backfill 2FA Secret từ Audit Log vào Master Workbook
Khi worker kích hoạt 2FA thành công trên thiết bị nhưng bước ghi vào Excel bị conflict file lock hoặc lỗi remote commit:
- Secret 2FA đã được lưu an toàn tại `$env:LOCALAPPDATA/tiktok-add-bao-mat-f2a/logs/2fa_audit.log` (trên máy local Kibe hoặc remote Admin).
- **Quy tắc đối soát 3 điểm**:
  1. Trích xuất `(May, Row, Username, 2FA_Secret)` từ `2fa_audit.log`, lấy bản ghi có timestamp mới nhất cho mỗi username.
  2. Mở Master Workbook, kiểm tra `cell_m == machine` và `cell_u.casefold() == username.casefold()`.
  3. Chỉ điền vào ô `2fa` nếu ô đó hiện đang trống (`not cell_2fa.value`). Không ghi đè nếu ô đã có secret khác trừ khi có yêu cầu rotation.
  4. Lưu workbook và xác nhận lại bằng read-back.

---

## 3. Kỷ luật State Persistence của Watchdog đa Phase
- Nếu Watchdog chạy chuỗi đa phase (e.g. Reg Gmail -> Add 2FA TikTok):
  - Tuyệt đối cấm gán `last_success_date = today` khi chỉ một phase đơn lẻ thành công (ví dụ: Gmail fail nhưng 2FA success).
  - Phải ghi nhận `lane_status = "failed"` và giữ nguyên `last_success_date` cũ để các tick cron tiếp theo tiếp tục chạy bù cho phase bị lỗi.
  - Chỉ ghi nhận `last_success_date = today` khi `lane_status == "success"`.
