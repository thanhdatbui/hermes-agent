# Đối soát Email Đã Có Tài Khoản TikTok (Live Screen vs Workbook Tracking)

## 1. Ngữ cảnh & Triệu chứng
Trong quá trình vận hành batch Đăng ký TikTok (`Tiktok_Reg / social_reg_v1.py`):
- Batch báo lỗi: `[07] Tat ca N email cua STT ... da co TK TikTok`.
- Người vận hành thường đặt câu hỏi nghi vấn: *Các email này đã được máy khác dùng rồi hay chưa? Thông tin tài khoản đăng ký lưu ở đâu?*

## 2. Bản chất kỹ thuật & Quy trình đối soát
Khi một email bị báo đã có tài khoản TikTok, có 2 trường hợp:

### Trường hợp A: Email đã đăng ký thành công trong hệ thống Farm
- **Vị trí lưu trữ:** Nằm trong file tracking chính `D:/OneDrive/TaadaaData/<profile>/taikhoan_dat_v2_updated .xlsx` (hoặc các file slot Tik1 -> Tik8).
- **Nhận diện:** Có đủ `Username`, `Password TikTok`, `UID`, ngày reg.
- **Xử lý:** Script tự động bỏ qua các email này ngay từ đầu nhờ hàm `load_registered_tiktok_emails()`.

### Trường hợp B: Email bị TikTok chặn do đã tồn tại tài khoản từ trước (Nguồn ngoài / Seller / Chưa tracking)
- **Hiện tượng:** Email nằm trong `gmail_clean_v2.xlsx` nhưng KHÔNG hề xuất hiện trong bất kỳ file Excel tracking hay cơ sở dữ liệu nào của Farm.
- **Cơ chế phát hiện:**
  1. Script nhập email vào form Đăng ký TikTok trên máy thật và bấm `Tiếp tục`.
  2. Server TikTok phát hiện email đã tồn tại và trả về UI:
     - Màn hình OTP: `Xác minh email` / `Sử dụng liên kết này hoặc nhập mã được gửi đến <email>...` / `Bạn cần trợ giúp đăng nhập?`.
     - Màn hình Password: `Nhập mật khẩu`.
  3. Script dump XML hiện trường (`D:/Taadaa/runtime/admin/artifacts/ui_dumps/fail_<stt>_email_already_registered_otp_*.xml`) và ghi log `DA CO TikTok va dang o OTP/verify → ABORT`.
  4. Tuân thủ **FARM-ASSET-001**: CẤM login đè / CẤM cướp tài khoản, script bấm `Back` để thử email tiếp theo.

## 3. Checklist điều tra nhanh O(1) khi gặp thắc mắc
1. **Kiểm tra chéo toàn bộ Excel Farm:** Quét nhanh qua script Python để khẳng định email có/không xuất hiện ở máy/slot khác.
2. **Kiểm tra XML hiện trường:** Mở file `fail_<stt>_email_already_registered_otp_*.xml` kiểm tra cụm text `Xác minh email` hoặc `f2k` để chứng minh TikTok live trả về OTP/login.
3. **Kết luận:** Nếu email chỉ có trong `gmail_clean_v2.xlsx` mà không có trong tracking, đó là do nguồn email đầu vào (Hotmail/Outlook) đã từng bị bên thứ 3 đăng ký TikTok từ trước.
