# Hotmail Security Script Excel Sheet Name Fallback & Recovery Reconciliation

## 1. Bản Chất Vấn Đề Lệch Sheet Name (`gmail_clean_v2.xlsx`)
Trong file `gmail_clean_v2.xlsx` (Single Source of Truth cho kho tài khoản):
- Sheet chính chứa danh sách tài khoản, mật khẩu, 2FA secret key và email khôi phục có tên là: **`'Gmail Accounts'`** (chứa cả Gmail lẫn Hotmail, 570+ rows).
- Trong các script tiện ích hoặc runner cũ (như `gpm_change_hotmail_security.py`):
  - Logic cũ: `ws = wb["Tài Khoản"] if "Tài Khoản" in wb.sheetnames else wb.active`
  - Vì trong `gmail_clean_v2.xlsx` **không hề có** sheet `'Tài Khoản'`, script fallback về `wb.active`.
  - Nếu active sheet bị trỏ sang sheet khác hoặc khi file được mở bằng library khác, việc tra cứu `get_recovery_email(email)`, `get_2fa_secret(email)` và cập nhật `update_excel_security_info()` sẽ thất bại hoặc trả về chuỗi rỗng (`""`).

## 2. Chuẩn Hóa Logic Mở Sheet Đa Tầng An Toàn
Mọi hàm đọc/ghi `gmail_clean_v2.xlsx` BẮT BUỘC phải ưu tiên `'Gmail Accounts'` trước:
```python
ws = (
    wb["Gmail Accounts"]
    if "Gmail Accounts" in wb.sheetnames
    else (wb["Tài Khoản"] if "Tài Khoản" in wb.sheetnames else wb.active)
)
```

## 3. Tác Động Đối Với Challenge Xác Minh Danh Tính Của Microsoft
Khi chạy đổi bảo mật Hotmail (`CHANGE_INFO`):
1. **Nếu không đọc được Recovery Email**:
   - Khi Microsoft yêu cầu xác minh danh tính qua mail khôi phục (`#proof-confirmation-email-input`), script không có email để điền -> văng lỗi `[-] Không tìm thấy mail khôi phục trong DB/Excel cho <email>` -> dừng ngay và bị đánh dấu `BLOCKED`.
2. **Khi đã sửa sheet name**:
   - Script tự động bốc đúng recovery email (ví dụ `<username>@fviainboxes.com` hoặc `@smvmail.com`).
   - Tự động gọi API mail domain (qua `mail_domain_otp_helper.py`) lấy mã 6 số OTP và tự động điền vào các ô OTP trên UI mới của Microsoft, vượt qua challenge hoàn toàn tự động.

## 4. Phân Loại Triage 53 Nick BLOCKED Sau Khi Vá
- **Nhóm đủ điều kiện chạy tự động**: Các nick đã có mặt trong `gmail_clean_v2.xlsx` VÀ Cột 5 (`mail khôi phục`) khác rỗng. Sau khi vá sheet name, nhóm này tự động giải được challenge khi Supervisor kích hoạt.
- **Nhóm thiếu Recovery Email**: Các nick có trong `gmail_clean_v2.xlsx` nhưng Cột 5 là `None` (31 nick) hoặc chưa có trong file (18 nick).
  - BẮT BUỘC tiếp tục giữ nguyên trạng thái fail-closed `BLOCKED`.
  - CẤM TUYỆT ĐỐI mở khóa hoặc retry tự động khi chưa bổ sung/backfill email khôi phục, vì Microsoft sẽ chặn đổi pass với lỗi *"Tạm thời có lỗi với dịch vụ"* và có nguy cơ khóa tài khoản vĩnh viễn.
