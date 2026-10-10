# Dual-Cluster 2FA Pitfalls: TikTok v46+ Email Unlink Block & SSH CLI Encoding (10/10/2026)

## 1. TikTok v46+ Email Unlink Block & `EMAIL_DISABLE_NOT_STABLE`

### Hiện tượng
- Chạy batch 2FA trên Farm Admin (hoặc máy chưa đồng bộ patch) báo: `Hoàn tất 0 | Lỗi 20`.
- Thư mục journals tích lũy nhiều file `.dpapi` (ví dụ 21 file) nhưng workbook Excel hoàn toàn không được ghi nhận 2FA mới.
- Các worker đều vượt qua bước submit OTP thành công, nhưng fail ngay sau đó và rollback/exit `failed`.

### Nguyên nhân gốc rễ
- Trên TikTok app v46+ (cụm Admin v46.6.3, Kibe v47.0.3), hệ thống TikTok chặn hoàn toàn thao tác gỡ/xóa Email đối với các tài khoản không liên kết Số điện thoại (SĐT).
- Hàm `_disable_email_and_confirm_stable` trong `live_phase_b_adapter.py` cố gắng bấm "Email" -> "Xóa" -> "Xác nhận", nhưng popup xóa bị chặn hoặc giao diện không cho phép gỡ email, dẫn đến timeout `EMAIL_DISABLE_NOT_STABLE`.
- Trên Kibe đã vá:
  ```python
  # BỎ BƯỚC GỠ EMAIL: TikTok v46+ chặn xóa email với tài khoản không có SĐT.
  return
  ```
- Tuy nhiên, patch này chưa được commit và deploy sang repo `D:/Taadaa/tiktok-add-bao-mat-f2a` trên máy Admin (`admin-farm`). Đồng thời, file trên Admin còn bị lỗi bảng mã tiếng Việt (Mojibake: `Xóa` biến thành `XA3a`, `Xác nhận` biến thành `XA-c nh-n`), khiến adapter văng lỗi 100%.

### Quy tắc bất biến
- BẮT BUỘC giữ Email khi bật 2FA trên TikTok v46+: chỉ bật Authenticator App và lưu mật khẩu, KHÔNG được cố gỡ Email.
- Mọi bản sửa logic adapter trong `tiktok-add-bao-mat-f2a` BẮT BUỘC phải đồng bộ cả 2 cụm Kibe (1-80) và Admin (201-280) trước khi kích hoạt batch runner.

---

## 2. Lỗi Transcode Bảng Mã CLI Qua SSH PowerShell (`--workbook-sheet`)

### Hiện tượng
- Gọi remote batch qua SSH PowerShell với EncodedCommand:
  `powershell -NoProfile -EncodedCommand ...`
  khi truyền tham số có dấu tiếng Việt như `--workbook-sheet 'Tài Khoản'`.
- Tham số khi vào Python trên máy đích bị biến dạng thành `--workbook-sheet 'Ti Kho?n'` do PowerShell chuyển đổi tham số sang OEM ANSI code page (CP1252/CP1258).
- Gây lỗi `WorkbookError("SOURCE_SHEET_MISSING")` hoặc sai lệch định danh sheet.

### Giải pháp chuẩn hóa
- Trong `run_batch_live_2fa.py`, biến `DEFAULT_SHEET = "Tài Khoản"` đã được hardcode chuẩn UTF-8 bên trong mã nguồn Python.
- Khi gọi lệnh qua SSH PowerShell, **KHÔNG truyền cờ `--workbook-sheet`** nếu đang dùng sheet mặc định, để Python tự load hằng số nội tại mà không qua lớp CLI parsing của Windows PowerShell.

---

## 3. Lỗi Đếm Trùng (Double Counting) Số Lượng Skip Trong Watchdog

### Hiện tượng
- Báo cáo watchdog hiển thị số lượng bỏ qua gấp đôi thực tế (ví dụ: `Bỏ qua 120` trong khi cụm Admin chỉ có 80 máy và tối đa 60-70 targets).

### Nguyên nhân
- Script `run_batch_live_2fa.py` in 2 bảng kết quả:
  1. `_print_results(results)`: in toàn bộ danh sách kết quả (bao gồm cả các dòng `skipped`).
  2. `if skipped: _print_results(skipped, title="Skip do device lock hoặc preflight")`: in lại riêng các dòng `skipped`.
- Regex của watchdog:
  `re.findall(r"^\s*(\d+)\s*\|\s*(\d+)\s*\|\s*[^|]+\|\s*(\w+)", output, re.M)`
  quét toàn bộ stdout và khớp cả 2 bảng, khiến mỗi target skip bị cộng 2 lần.

### Giải pháp
- Khi parse bảng output của `run_batch_live_2fa.py`, chỉ parse bảng đầu tiên hoặc deduplicate theo cặp `(machine, source_row)`.

---

## 4. Timeout Chuỗi Tuần Tự Do Thiết Bị Offline Trong Vòng Lặp Preflight

### Hiện tượng
- Trước khi worker song song được khởi chạy, hàm `main()` của `run_batch_live_2fa.py` duyệt tuần tự qua danh sách `targets` để acquire device lock và chạy `require_android_vpn`.
- Nếu có thiết bị đang ở trạng thái `offline`, `CoreAdbClient` sẽ kích hoạt cơ chế tự phục hồi: gọi `reconnect` và `wait-for-device` (timeout 20s) lặp lại 3 lần = 60s/thiết bị.
- Nếu có 5-6 máy offline, vòng lặp preflight bị nghẽn tới 5-6 phút trước khi ThreadPoolExecutor kịp chạy máy đầu tiên.

### Giải pháp
- Đảm bảo preflight loại trừ hoặc kiểm tra nhanh danh sách thiết bị online từ `adb devices` trước khi bước vào vòng lặp acquire lock tuần tự.
