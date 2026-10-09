# Dual Cleanup Rule: Gmail DIE Phải Dọn Cả Excel Lẫn Thiết Bị S7 (2026-09-17)

## Nguyên Tắc Bắt Buộc Từ User
> "khi gmail die ở khâu check live thì nhớ dọn ở cả máy nhé chứ k chỉ ở excel đâu"

Khi bất kỳ cơ chế nào (Preflight check live qua web `checkmail.live`, script quét định kỳ, hoặc lỗi OTP timeout) phát hiện một tài khoản Gmail đã bị vô hiệu hóa / DIE:
1. **Dọn dẹp nguồn Excel**:
   - Gọi `remove_captcha_dead_email_from_source(email)` xóa dòng khỏi `gmail_clean_v2.xlsx`.
   - Ghi vết vào `D:/OneDrive/TaadaaData/kibe/gmail_die_tong.txt`.
2. **Dọn dẹp ngay trên thiết bị Android (Samsung S7)**:
   - **Tuyệt đối không bỏ quên tài khoản DIE trên máy**, vì nó sẽ làm đầy slot Google Accounts, gây kẹt sync và làm hỏng các lượt reg tiếp theo.
   - Gọi module chuẩn: `D:/Taadaa/tools/remove_device_google_account.py` qua hàm `remove_device_account_fast(serial, email)`.
   - Cơ chế hoạt động:
     + Quét nhanh `dumpsys account`: nếu tài khoản không có trên máy -> return `True` O(1) an toàn.
     + Nếu tài khoản còn trên máy -> điều hướng `Settings -> Accounts -> Google -> Remove account` bằng ADB UI để gỡ sạch.
