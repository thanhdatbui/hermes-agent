# Kiến Trúc Nuôi Dưỡng & Vòng Đời Gmail Farm (S7 Physical -> GPM PC -> OmniRoute)

## 1. Bối Cảnh & Nguyên Lý Cốt Lõi (Google Identity Risk Engine)
- **2FA TOTP Không Tăng Trust Score Nhưng Là "Lá Chắn Thoát Hiểm" Sống Còn**:
  - 2FA TOTP chỉ chứng minh không bị cướp mật khẩu, không chứng minh là người thật.
  - TUY NHIÊN, khi chuyển từ điện thoại Android S7 (môi trường gốc) lên PC Chromium GPM (thiết bị mới, IP mới), Google Risk-Based Authentication (RBA) bắt buộc kích hoạt Secondary Challenge.
  - Nếu KHÔNG CÓ 2FA: Google kích hoạt phòng thủ cao nhất -> Ép vào Phone SMS Checkpoint (`challenge/iap`). Không có SIM là chết tài khoản ngay.
  - Nếu CÓ 2FA TOTP: Google hỏi mã Authenticator 6 số. Điền mã từ Excel -> Vượt qua checkpoint mượt mà không bị hỏi SMS. BẮT BUỘC BẬT 2FA TRÊN S7 TRƯỚC KHI MANG LÊN PC.

- **Developer API vs Consumer Activity**:
  - Quyền Antigravity (Google Cloud Developer API / Code Assist) nằm ở tầng kiểm soát lạm dụng (Cloud Abuse Detection).
  - Vừa login GPM mà bấm cấp quyền Cloud API ngay trong Session 1 -> Ăn cờ "New Device Anomaly + Developer Privilege Escalation" -> Chết hàng loạt sau 30-45 ngày.
  - CẤM OAuth Antigravity ngay khi vừa login GPM. Phải ngâm profile GPM >= 7 ngày và có hoạt động Consumer thật rồi mới được OAuth Antigravity.
  - Ngược lại, OAuth ChatGPT-Web là dịch vụ ngoài (Third-party consumer), hoàn toàn lành tính, lấy ngay sau khi login GPM.

## 2. Chu Trình Vòng Đời 4 Pha Chuẩn Hóa
1. **Pha 1 (S7 Physical Phone)**:
   - Reg Gmail trên Android S7 qua proxy 4G di động MobiFone.
   - Reg ngay ChatGPT trên Chrome S7 bằng Direct Email OTP (nhận mail OpenAI để tạo vết sinh hoạt đầu tiên).
   - Bật 2FA TOTP trên S7 (ADB bốc mã 10 số hardware) -> Lưu Secret Key 32 ký tự vào Excel.
   - Ngâm tĩnh >= 7 ngày trên S7 (duy trì Auto-Sync nhận push notification).
2. **Pha 2 (Đăng nhập GPM PC & Khai thác ChatGPT-Web)**:
   - Sau 7 ngày trên S7, đăng nhập vào profile GPM qua proxy 4G tương ứng.
   - Vượt checkpoint bằng Mật khẩu + giải mã TOTP 2FA từ Excel.
   - Đăng nhập lấy ngay session token ChatGPT-Web nạp vào OmniRoute Pool.
   - Chạy module Noise Injection (YouTube + Search) 60-90s trước khi đóng profile.
3. **Pha 3 (Nuôi Định Kỳ Tự Động Trên GPM - cron_gpm_gmail_nurture.py)**:
   - Chạy độc lập trên PC cả ngày (09:00, 11:00, 13:00, 15:00, 17:00, 19:00, 21:00), KHÔNG đụng tới S7/ADB.
   - Áp dụng Staggered Launch (khởi động so le 45-60s) + Exclusivity Proxy (1 profile / 1 proxy 4G) để chống gom cụm đồng pha trên máy Dual Xeon.
   - Tần suất: 5-7 ngày / lượt / tài khoản (state JSON quản lý).
   - Kịch bản trong profile:
     + Xáo trộn ngẫu nhiên thứ tự 3 tác vụ: YouTube, Google News, Google Search.
     + YouTube: Xử lý trang chủ trống (lướt Shorts 6s -> về Home bung 30 video đề xuất) -> Lọc bỏ 100% thẻ "Được tài trợ" (Sponsored/Ad) -> Bắt buộc vào `/watch?v=...` thật -> Smart Ad Skip (70% đợi 7-10s bấm Skip, 30% để chạy tự nhiên) -> Xem video 90-120s (mốc vàng nạp AdSense cookie & heartbeat).
     + Google News: Mở `news.google.com`, click mở bài báo thật sang tab mới, đọc bài 45-60s kết hợp cuộn trang ngắt quãng (human scroll). Chấp nhận cả báo tiếng Anh và tiếng Việt (tự nhiên với người dùng).
     + Google Search: Tìm từ khóa đời sống ngẫu nhiên và dừng lại 10-15s.
     + Chụp screenshot nghiệm thu qua CDP trực tiếp không chờ web fonts.
4. **Pha 4 (Van An Toàn Kích Hoạt Antigravity)**:
   - Chỉ kích hoạt OAuth Antigravity khi profile GPM đã ngâm >= 7 ngày (`is_profile_aged_7_days`).
   - Timeout OAuth nâng lên 120s để xử lý trễ mạng 4G.

## 3. Các Bẫy Triển Khai Thực Tế Cần Tránh
- **Bẫy Trang Chủ YouTube Trống ("Thử tìm kiếm để bắt đầu")**:
  - Tài khoản mới chưa có lịch sử xem, YouTube hiển thị feed trắng tinh. Bấm F5 hoàn toàn vô tác dụng.
  - Cách giải quyết: Click tab Shorts lướt 5-8s rồi click lại Trang chủ (Home) -> Feed YouTube lập tức bung ra ~30 video.
- **Bẫy Selector Nút Bỏ Qua Quảng Cáo**:
  - YouTube hiện đại dùng class `.ytp-skip-ad-button` hoặc `.ytp-ad-skip-button-modern`.
  - Không click ngay ở giây thứ 5.0 (dấu hiệu bot). Phải đợi ngẫu nhiên đến giây 7-10 mô phỏng phản xạ người thật.
- **Bẫy Screenshot Timeout Trên YouTube / GPM**:
  - `page.screenshot` bằng Playwright thường bị kẹt do web fonts của YouTube tải chậm quá 5000ms.
  - Giải pháp: Dùng CDP trực tiếp qua `context.new_cdp_session(page).send("Page.captureScreenshot", {"format": "jpeg", "quality": 80})` chạy tức thì không chờ fonts.
- **Bẫy Đồng Pha Khi Chạy Trạm Dual Xeon**:
  - Máy Dual Xeon mở nhiều profile cùng lúc qua các proxy 4G khác nhau VẪN BỊ GOOGLE GOM CỤM nếu mở đồng loạt cùng một giây (cùng chữ ký phần cứng, cùng nhịp request).
  - Bắt buộc phải có Staggered Launch (giãn cách mở profile 45-60s) và Random Jitter.
