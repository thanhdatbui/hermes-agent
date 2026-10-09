# Google Identity Risk Engine, 2FA Fallback & Lifecycle Pipeline (S7 -> GPM -> OmniRoute)

## 1. Bản Chất Rủi Ro Danh Tính (Identity Risk Scoring & Graph Analytics)
- **Hiểu lầm phổ biến: 2FA TOTP ≠ Tăng Trust Score**:
  - 2FA TOTP không chứng minh "đây là con người thật đang sinh hoạt". Nó chỉ chứng minh kẻ tấn công không có mật khẩu thứ hai.
  - Tuy nhiên, **2FA TOTP BẮT BUỘC PHẢI CÓ** vì nó là **"Lá chắn thoát hiểm" (Deterministic Challenge Bypass)**. Khi chuyển tài khoản từ môi trường điện thoại S7 lên máy tính PC (trình duyệt Chromium GPM qua proxy mới), Risk-Based Authentication (RBA) của Google luôn kích hoạt thử thách xác minh thứ hai (Secondary Challenge).
  - **Nếu KHÔNG có 2FA**: Google không có phương thức xác minh nào khả dụng, lập tức ép sang Phone SMS Checkpoint (`challenge/iap`). Nếu không có SIM vật lý, tài khoản chết ngay.
  - **Nếu CÓ 2FA TOTP**: Google ưu tiên hỏi mã 6 số từ Google Authenticator -> Script điền tự động từ Excel -> Vượt qua xác minh IP mới mượt mà, triệt tiêu nguy cơ dính SMS Checkpoint.

## 2. Phân Tầng Rủi Ro Cấp Quyền OAuth (ChatGPT vs Google Antigravity)
- **ChatGPT-Web OAuth (Low-Risk Consumer Scope)**:
  - Thuộc dịch vụ bên thứ ba (OpenAI), nằm ngoài hệ sinh thái Google.
  - Người thật vừa login Google trên PC thường liên kết ngay với các dịch vụ web tiêu dùng (ChatGPT, Spotify, Shopee...).
  - Hành vi này lành tính, thậm chí tạo thêm vết sinh hoạt uy tín (Activity Stream). Do đó **ĐƯỢC PHÉP LẤY CHATGPT-WEB NGAY SAU KHI LOGIN GPM THÀNH CÔNG**.
- **Google Antigravity OAuth (High-Risk Developer/Cloud Scope)**:
  - Antigravity xin quyền vào Google Cloud Platform / Code Assist Developer API (`cloudaicompanion.googleapis.com`, `googleapis.com/auth/cloud-platform`).
  - Google Fraud Management System (FMS) coi đây là mục tiêu hàng đầu của các botnet farm tài nguyên Cloud.
  - Một profile GPM mới xuất hiện trên PC mà ngay trong Phiên 1 đã bấm xin quyền Developer Cloud API sẽ bị cắm cờ: **"New Device Anomaly + Developer Privilege Escalation"**. Xác suất bị khóa hoặc bắt xác minh danh tính > 90%.
  - **BẤT BIẾN AN TOÀN**: **TUYỆT ĐỐI KHÔNG OAUTH ANTIGRAVITY LIỀN TAY**. Bắt buộc hoãn (aging profile) tối thiểu 7 ngày trên GPM có sinh hoạt tự nhiên rồi mới cấp quyền Antigravity.

## 3. Workflow 7 Bước Chuẩn Tuyệt Đối (S7 Farm -> GPM -> OmniRoute)
1. **Bước 1 (Reg S7)**: Đăng ký Gmail sạch trên điện thoại Samsung S7 vật lý (IP 4G di động sạch).
2. **Bước 2 (ChatGPT Link)**: Ngay sau khi reg, dùng Chrome trên S7 đăng ký tài khoản ChatGPT bằng Direct Email OTP (nhận thư OpenAI kích hoạt vết sinh hoạt đầu tiên, tuyệt đối không dùng Google SSO).
3. **Bước 3 (Bật 2FA S7)**: Bật 2FA TOTP (Google Authenticator) ngay trên S7 (kết hợp ADB lấy mã 10 số hardware của chính S7) -> Lưu Secret Key 32 ký tự vào `master_gmail_manager.xlsx` và `gmail_clean_v2.xlsx`.
4. **Bước 4 (Ngâm S7)**: Ngâm tĩnh >= 7 ngày trên S7 (duy trì bật Auto-Sync để máy nhận push notification bình thường).
5. **Bước 5 (Login GPM)**: Sau 7 ngày, mang lên PC đăng nhập vào profile Chromium GPM qua proxy 4G tương ứng (điền User/Pass + giải mã TOTP 2FA tự động từ Excel, vượt checkpoint an toàn).
6. **Bước 6 (Kéo ChatGPT-Web + Pha loãng hành vi)**:
   - Lấy cookie session `__Secure-next-auth.session-token` đồng bộ vào ChatGPT-Web Pool trên OmniRoute (:20129) để dùng ngay.
   - **Pha loãng hành vi (Noise Injection & Identity Warming)**: Mở tab `youtube.com` xem 1 video ngẫu nhiên từ 45-60s, sau đó tìm kiếm 1 từ khóa đời sống trên Google Search (10-15s) rồi mới đóng profile.
   - Ghi nhận `gpm_login_date` và đánh cờ `antigravity_eligible_date = today + 7 days`.
7. **Bước 7 (Cấp quyền Antigravity sau 7 ngày ngâm GPM)**:
   - Profile GPM sau khi ngâm đủ >= 7 ngày trên PC đã biến thành "Thiết bị quen thuộc" (Trusted Device).
   - Watchdog kiểm tra cờ đủ điều kiện mới mở profile thực hiện luồng Silent OAuth Antigravity và nạp vào Antigravity Pool trên OmniRoute.

## 4. Kỷ Luật Phân Bổ Lịch Cron & Farm Alert
- **Chống xung đột lịch chạy**: Phân bổ tác vụ vào các khoảng nghỉ sinh học giữa các ca nuôi feed TikTok (07:15-08:45 sáng, 12:00-13:45 trưa, 20:15-23:45 tối). Mọi script can thiệp thiết bị bắt buộc kiểm tra `acquire_device_lock` và `MIN_IDLE_BUFFER_MIN = 45 phút`.
- **Báo cáo Farm Alert (`telegram:-5373649734`)**: Mọi watchdog quản lý pool tài khoản và login GPM bắt buộc cấu hình `deliver: telegram:-5373649734`, tuân thủ nguyên tắc Silent Watchdog (im lặng khi bình thường, chỉ báo cáo khi có hành động/hồi sinh/lỗi).
