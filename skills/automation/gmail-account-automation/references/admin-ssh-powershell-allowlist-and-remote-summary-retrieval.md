# Admin SSH PowerShell Allowlist & Summary Retrieval Pitfalls

## 1. Hiện tượng & Vấn đề (Báo cáo gộp bị thiếu số liệu cụm Admin)
Khi một kịch bản điều phối (như `cron_night_tiktok_2fa_watchdog.py`) gửi lệnh PowerShell qua `admin_ssh.py` để lấy file kết quả `summary.json` từ cụm Admin:
```python
# Cú pháp bị lỗi kẹt Allowlist / DateTime parser
ps_cmd = (
    f"$min = [DateTimeOffset]::FromUnixTimeSeconds({int(min_mtime)}).LocalDateTime; "
    "$items = Get-ChildItem -Path 'D:\\CodexRuntime\\...\\summary.json' ... | "
    "Where-Object { $_.LastWriteTime -ge $min } | Sort-Object LastWriteTime -Descending; "
    "if ($items) { Get-Content $items[0].FullName -Raw -Encoding UTF8 }"
)
```
- **Lỗi 1 (COMMAND_NOT_IN_ALLOWLIST):** Bắt đầu lệnh bằng biến `$min` hoặc `$items = ...` sẽ bị `admin_ssh.py` chặn ngay lập tức vì không bắt đầu bằng prefix được phép trong allowlist (`Get-`, `Set-`, `python`, `cat`...).
- **Lỗi 2 (Allowlist Prefix Gating):** Lệnh bắt buộc phải mở đầu trực tiếp bằng cmdlet được phép, ví dụ `Get-Content ...` hoặc `Get-ChildItem ...`.

## 2. Kỹ thuật truy vấn chuẩn qua `admin_ssh.py`
Để lấy `summary.json` mới nhất từ remote Admin mà không bị chặn allowlist:
```powershell
Get-Content (Get-ChildItem -Path 'D:\CodexRuntime\codex_gmail_debug-register-gmail\logs_parallel_*\summary.json' | Sort-Object LastWriteTime -Descending | Select-Object -First 1).FullName -Raw -Encoding UTF8
```
- Lệnh mở đầu bằng `Get-Content`, thỏa mãn `ALLOWED_COMMAND_PREFIXES` trong `admin_ssh.py`.
- Tự động lấy file `summary.json` mới nhất mà không cần truyền biến trung gian `$items` hay tính toán timestamp phức tạp dễ lệch format locale giữa các máy Windows.

### Lọc theo thời gian an toàn không bị chặn allowlist:
Nếu cần lọc theo ngưỡng thời gian (ví dụ trong 12 giờ qua hoặc theo Unix epoch):
```powershell
Get-ChildItem -Path 'D:\CodexRuntime\codex_gmail_debug-register-gmail\logs_parallel_*\summary.json' -ErrorAction SilentlyContinue | Where-Object { $_.LastWriteTime -ge [DateTimeOffset]::FromUnixTimeSeconds(<epoch>).LocalDateTime } | Sort-Object LastWriteTime -Descending | Select-Object -First 1 | ForEach-Object { Get-Content $_.FullName -Raw -Encoding UTF8 }
```
- Mở đầu trực tiếp bằng `Get-ChildItem` (prefix `Get-` nằm trong allowlist của `admin_ssh.py`), tuyệt đối KHÔNG gán `$min = ...` ở đầu câu lệnh.
- Stream JSON trực tiếp qua `ForEach-Object { Get-Content ... }` để `admin_ssh.py` đọc về Python sạch sẽ.

## 3. Đối soát hình ảnh màn hình Phone Checkpoint (WinRT OCR)
- Khi Google kích hoạt Phone Verification sau bước Password, ảnh chụp được lưu tại:
  `C:\Users\<user>\AppData\Local\register-gmail\screenshots\phone_verify_<stt>_after_pass_<time>.png`
- Dùng `automation_core.ocr.ocr_screen_boxes` hoặc `automation_core.ui_extract.extract_ui` với WinRT OCR để đọc chữ trực tiếp trên ảnh xác minh tiêu đề:
  - `"Xác minh số điện thoại của bạn"` / `"Google cần xác minh thiết bị hoặc số điện thoại"`
  - Nút bấm: `"Sử dụng thiết bị khác"` và `"Xác minh"`.
- Tuyệt đối soi mắt bằng OCR trước khi kết luận hoặc đính kèm `MEDIA:<path>` cho người dùng theo Invariant Gate 6.
