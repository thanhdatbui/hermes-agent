# Quy tắc mật khẩu và khôi phục tài khoản TikTok bị lệch pass qua Hotmail

## 1. Quy tắc mật khẩu bắt buộc
- **CẤM TUYỆT ĐỐI** dùng mật khẩu có đuôi `@Ks` cũ (ví dụ `Susan123@Ks`).
- Khi cần tạo hoặc đổi mật khẩu: Bắt buộc dùng `generate_account_password()` từ `D:/Taadaa/tiktok-add-bao-mat-f2a/python_runner/core/passwords.py` để sinh chuỗi ngẫu nhiên 16-18 ký tự mạnh (có chữ hoa, thường, số, dấu `-`).
- Khi reg nick mới: Nếu TikTok không yêu cầu đặt pass, cột PASS trong Excel **BẮT BUỘC ĐỂ TRỐNG (`None`/`""`)**, tuyệt đối không tự bịa pass ảo ghi vào file.

## 2. Khôi phục nick lệch pass qua Web Reset
- Trên thiết bị mới (chưa đủ Trust score), App TikTok thường đá văng khi bấm "Đặt lại mật khẩu bằng email".
- Giải pháp: Dùng Chrome web (`https://www.tiktok.com/login/email/forget-password`) gửi mã OTP về Hotmail -> Đọc OTP từ Hotmail (qua Graph API hoặc web Outlook) -> Đặt mật khẩu mạnh mới -> Đăng nhập vào App TikTok -> Đồng bộ pass mới vào toàn bộ Excel (`taikhoan_dat_v2_updated .xlsx`, `taikhoan_run_safe.xlsx`, `Tik*.xlsx`).
- Chu kỳ thử lại an toàn tránh rate-limit: 1h đến 6h (khung 6h tránh trùng lịch dọn cache đêm 01:00-04:50).
