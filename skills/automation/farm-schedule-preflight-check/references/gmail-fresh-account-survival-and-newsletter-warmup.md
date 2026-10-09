# Gmail Fresh-Account Survival & Newsletter Warmup Hook (12/09/2026)

## 1. Bản Chất Hiện Tượng & Nguyên Nhân Quét DIE Sau 48H (Root Cause)
- **Tài khoản ma (Ghost Account):** Gmail reg xong không có bất kỳ tương tác gửi/nhận nào sẽ bị thuật toán Google AI xếp vào diện tài khoản ảo dùng cho mục đích spam. Sau 24h - 72h quét định kỳ, Google sẽ khóa ngầm hoặc ép xác minh SMS.
- **Footprint Bot trong Format Tên & Mật Khẩu:**
  * Sinh username theo pattern cố định (`ho + ten + DOB + số máy` hoặc gắn suffix `media`, `plus`, `work`, `tech`, `online`, `top`).
  * Mật khẩu dùng chung signature (ví dụ đuôi `@Ks`, `@Safe`).
  * Google AI nhận diện mẫu số chung giữa các tài khoản được sinh ra từ cùng dải IP/nhà mạng và tiến hành chain-ban diện rộng.

## 2. Giải Pháp Warmup Hộp Thư Tự Động (Inbound Welcome Traffic)
- **Cơ chế:** Ngay khi một tài khoản Gmail vừa tạo thành công (`persist_success_result`), script tự động gửi request đăng ký nhận bản tin (Newsletter Subscription) công khai từ các hệ thống tin tức công nghệ uy tín thế giới (Node Weekly, JavaScript Weekly, Ruby Weekly, Postgres Weekly...).
- **Hiệu ứng Trust:** Các dịch vụ này lập tức gửi email chào mừng (Welcome Email / Confirmation Mail) về hộp thư Gmail. Google ghi nhận hộp thư có tương tác và hoạt động thực tế, thoát khỏi bộ lọc quét tài khoản ma.
- **Triển khai:** Module `D:/Taadaa/tools/warmup_newsletter_services.py` được gọi tự động trong `gmail_reg_v10.py`.

## 3. Quy Hoạch Bật 2FA Sau 48H Ngâm (Khung Giờ Vàng 15:00)
- **Cấm bật 2FA ngay lúc reg:** Google kích hoạt cờ *Fresh Account Security Delay / Loop Verification* làm xóa trắng form xác minh mật khẩu.
- **Khung giờ chạy lý tưởng:** **15:00 hàng ngày** (ngay sau khi Ca Trưa nuôi acc 12:00 - 14:00 kết thúc hoàn toàn).
- **Tránh khung giờ đêm / tối:** Tuyệt đối không bật 2FA vào buổi tối (18:00 - 23:00) hoặc đêm (00:00 - 02:00) để không giẫm chân vào chuỗi reg Gmail/TikTok ban đêm (`night-chain-reg-pipeline` lúc 01:00).
- **Bộ lọc tuổi ngâm:** Chỉ chọn tài khoản **ngâm $\ge 48$ giờ** (`days_ago >= 2`).
