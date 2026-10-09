# Canonical Sheet Filter & Fail-Soft Domain Resolution (2026-09-25)

## Bối cảnh & Vấn đề
Khi file tracking workbook chứa nhiều sheets (bao gồm các sheet nháp/audit như `"Khong Co Trong GmailClean"`, `"Máy Thiếu Acc"`, `"Audit Pending"`), `load_tracking_accounts_for_stt` trong `tiktok_login_v1.py` trước đây quét toàn bộ sheets:
1. Gây trùng lặp account khi một tài khoản xuất hiện ở cả sheet chính lẫn sheet audit.
2. Dữ liệu trên sheet audit có thể chưa chuẩn hóa (ví dụ email chỉ có local-part thiếu `@gmail.com`), dẫn đến lỗi `email_missing_domain`.
3. Hàm `resolve_missing_domains_from_device` trước đây buộc phải tìm thấy Gmail live trên thiết bị qua `live_gmail_accounts()`, nếu không tìm thấy sẽ văng `RuntimeError`, chặn đứng luồng đăng nhập ngay cả khi account có đầy đủ ID + Pass (không cần OTP email).

## Giải pháp triển khai trong `tiktok_login_v1.py`

### 1. Chỉ nạp sheet chính chủ trong `load_tracking_accounts_for_stt`
- Ưu tiên sheet `"Tài Khoản"` nếu tồn tại.
- Nếu không có, tìm sheet `"Accounts"`.
- Nếu cả hai đều không có, nạp các sheet không nằm trong blacklist audit:
  `("Khong Co Trong GmailClean", "Máy Thiếu Acc", "Audit Pending")`.

### 2. Ưu tiên canonical sheet trong `pick_accounts`
Khi truyền `--email <ID_hoặc_Email>` và tìm thấy nhiều hơn 1 dòng trùng khớp:
- Ưu tiên giữ lại account thuộc sheet `"Tài Khoản"` hoặc `"Accounts"`.
- Nếu vẫn hòa, ưu tiên account không có issue `email_missing_domain`.

### 3. Fail-soft Domain Resolution trong `resolve_missing_domains_from_device`
Khi local-part không khớp với Gmail live nào trên máy:
- Nếu account có cả `id` và `tiktok_pass` đồng thời không bật `--otp-only` (`not acc.get("otp_only")`):
  -> Fail-soft tự động gắn `@gmail.com` và ghi log cảnh báo:
  `[gmail-check] warn: Khong tim thay Gmail live tren may cho '...', fallback inferred: ...@gmail.com (ID+Pass login)`
- Nếu là `--otp-only` hoặc thiếu ID/Pass:
  -> Vẫn raise `RuntimeError` để bảo vệ an toàn quy trình nhận mã OTP.

## Unit Tests
Được kiểm chứng tại:
- `tests/test_tiktok_login_sheet_filter.py`: Kiểm chứng nạp sheet chính chủ, ưu tiên canonical trong `pick_accounts`, và 2 nhánh fallback / raise của `resolve_missing_domains_from_device`.
- `tests/test_tiktok_login_otp_only.py`: Đảm bảo `sys.path` nạp đúng `REPO_ROOT` khi test độc lập.
