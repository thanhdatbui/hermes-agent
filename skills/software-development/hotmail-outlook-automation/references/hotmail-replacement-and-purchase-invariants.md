# Hotmail Replacement & Purchasing Invariants (2026-10-01)

## 1. CẤM BỐC MAIL MÁY KHÁC ĐẮP SANG MÁY LỖI
- Tuyệt đối KHÔNG lấy mail đang được phân bổ trong `gmail_clean_v2.xlsx` hoặc danh sách slot reg chờ của máy khác (ví dụ: mail đang gán cho STT 76) để đổi sang profile lỗi của máy khác (ví dụ: Máy 34).
- Mail dùng để thay thế BẮT BUỘC phải là mail thừa tự do, chưa từng được ghi nhận trong bất kỳ hàng nào của `taikhoan_dat_v2_updated .xlsx` lẫn `gmail_clean_v2.xlsx`.
- Đối soát tính khả dụng của mail:
  * Mail phải có Microsoft Graph OAuth2 token hợp lệ (HTTP 200).
  * Mail KHÔNG nằm trong `registered_emails_blacklist.json`.
  * Mail CHƯA từng nhận thư xác nhận từ TikTok (kiểm tra inbox qua Graph API trước khi điền).

## 2. THAO TÁC TỐN PHÍ BẮT BUỘC HỎI SẾP (ZERO UNSANCTIONED BUYING)
- Mọi thao tác phát sinh chi phí tiền thật (mua Hotmail qua `buy_hotmail.py`, thuê SMS qua 5SIM, giải Captcha trả phí) BẮT BUỘC PHẢI HỎI SẾP trước khi thực hiện.
- CẤM TUYỆT ĐỐI agent tự ý gọi script/API mua tài khoản khi chưa có sự xác nhận của người dùng.

## 3. PHÂN BIỆT BLACKLIST TIKTOK VS GPM CHATGPT
- `registered_emails_blacklist.json` trong `D:/Taadaa/Tiktok_Reg/data/` CHỈ dùng cho tiến trình reg TikTok trên máy Android, nhằm tránh thử lại email đã từng tạo TikTok.
- Tool GPM reg ChatGPT (`batch_gpm_5profiles_supervisor.py`) hoàn toàn KHÔNG đọc và KHÔNG bị ảnh hưởng bởi file blacklist của TikTok.
- Email bị đưa vào blacklist TikTok vẫn có thể dùng để đăng nhập và reg ChatGPT trên GPM bình thường nếu mật khẩu và token Microsoft còn sống.
