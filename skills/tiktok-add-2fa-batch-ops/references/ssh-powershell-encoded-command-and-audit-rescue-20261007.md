# SSH PowerShell EncodedCommand & 2FA Audit Rescue Protocol (2026-10-07)

## 1. Bẫy Mã Hóa Ký Tự Unicode & Khoảng Trắng Qua SSH Windows PowerShell
Khi Coordinator điều phối gọi tiến trình trên máy phụ (`admin-farm`) qua OpenSSH:
- Lệnh gọi trực tiếp:
  ```bash
  ssh admin-farm "powershell -NoProfile -Command \"... --workbook-sheet 'Tài Khoản' --workbook-path 'D:/.../taikhoan_dat_v2_updated .xlsx'\""
  ```
- **Hậu quả**:
  1. Ký tự tiếng Việt có dấu (`Tài Khoản`) bị Windows console / charmap chuyển đổi sai lệch hoặc ném `UnicodeEncodeError: 'charmap' codec can't encode character...`.
  2. Khoảng trắng trong tên file (`updated .xlsx`) bị PowerShell phân tách thành nhiều tokens, gây lỗi `argparse: unrecognized arguments: .xlsx`.
  3. Runner thoát sớm với exit code 1/2, báo cáo telemetry sai lệch thành "bỏ qua 96 / lỗi 32" khiến coordinator hiểu nhầm là nick đã có sẵn 2FA.

- **Giải pháp chuẩn hóa (PowerShell EncodedCommand)**:
  Bọc toàn bộ script trong UTF-16LE Base64 trước khi truyền qua SSH:
  ```python
  import base64

  ps_script = (
      "$env:PYTHONIOENCODING = 'utf-8'\n"
      "$env:PYTHONUTF8 = '1'\n"
      "Set-Location 'D:/Taadaa/tiktok-add-bao-mat-f2a'\n"
      "$wb = 'D:\\OneDrive\\TaadaaData\\admin\\taikhoan_dat_v2_updated .xlsx'\n"
      "& 'D:\\Taadaa\\python-envs\\automation\\Scripts\\python.exe' python_runner/run_batch_live_2fa.py "
      "--workbook-path $wb --workbook-sheet 'Tài Khoản' --max-workers 40 --live\n"
  )
  b64_ps = base64.b64encode(ps_script.encode("utf-16le")).decode("ascii")
  cmd = ["ssh", "-o", "ConnectTimeout=10", "admin-farm", f"powershell -NoProfile -EncodedCommand {b64_ps}"]
  ```

---

## 2. Quy Trình Cứu Hộ Secret 2FA Từ Audit Log Sau Sự Cố Ghi Workbook (Cross-Host Backfill)
Khi Phase B trên máy Android đã hoàn tất (đã liên kết Authenticator thành công trên app TikTok) và ghi log vào `2fa_audit.log` hoặc `.dpapi` journal trên máy đích, nhưng bước cập nhật file Excel Master bị chặn:
- **Tuyệt đối cấm chạy lại từ đầu**: Chạy lại sẽ bị chặn bởi màn hình 2FA đã bật hoặc làm hỏng secret key đang lưu trong app.
- **Quy trình trích xuất & backfill**:
  1. Đọc audit log từ máy đích:
     `$env:LOCALAPPDATA/tiktok-add-bao-mat-f2a/logs/2fa_audit.log` (hoặc qua SSH nếu là cluster remote).
  2. Parse pattern:
     `May: (?P<machine>\d+) \| Sheet:[^|]+\| Row: (?P<row>\d+) \| Username: (?P<username>[^|]+) \| 2FA_Secret: (?P<secret>[A-Z0-9]+)`
  3. Lấy secret mới nhất theo từng tài khoản `(machine, username)`.
  4. Đối chiếu với file Master Excel tương ứng (`kibe` hoặc `admin`), điền trực tiếp giá trị `secret` vào cột `2FA` của sheet `Tài Khoản`.
  5. Chạy đối soát chéo 3 lớp: `tiktok_tracker.db` ↔ `2fa_audit.log` ↔ Master Workbook để đảm bảo 100% tài khoản khớp số liệu.
