# Kiến Trúc Nuôi Dưỡng Gmail Định Kỳ & Warming Trên GPMLogin (Chống Quét Cụm Google)

## 1. Triết Lý Cốt Lõi: Identity Entropy & Tránh Bẫy "Đồng Pha"
- **2FA TOTP Không Phải Để Tăng Trust**: 2FA không chứng minh tài khoản là người thật; nó đóng vai trò là "Lá chắn thoát hiểm" (Deterministic Challenge Bypass) để Google không hỏi SMS số điện thoại (`challenge/iap`) khi đổi thiết bị từ điện thoại Android S7 lên PC (GPM Chromium).
- **Phân Tầng Rạch Ròi 2 Hệ Sinh Thái**:
  - *Consumer Footprint (YouTube, News, Search, Gmail)*: Tăng Human Score và bảo vệ tài khoản sống lâu.
  - *Developer API (Antigravity / Google Cloud Code Assist)*: Là nơi bị quét lạm dụng API (Abuse Detection). Tuyệt đối KHÔNG cấp quyền Developer API ngay trong phiên đầu tiên (Session 1) trên GPM. Bắt buộc ngâm profile GPM >= 7 ngày mới được cấp quyền Antigravity.
- **Phá Vỡ Đồng Pha Trên Trạm Dual Xeon**: Dù máy trạm Xeon có thể gánh hàng chục profile cùng lúc và mỗi profile dùng 1 proxy 4G riêng biệt, việc khởi động đồng loạt trong cùng một giây sẽ bị Google gom cụm theo chữ ký phần cứng và thời gian. Bắt buộc áp dụng **Staggered Launch** (khởi động so le cách nhau 45 - 90 giây) kết hợp **Randomized Jitter** thời gian xem.

## 2. Quy Trình 3 Bước Nuôi Tài Khoản Chuẩn (GPM Profile)
1. **YouTube Thường (Mốc vàng 90 - 120 giây)**:
   - **Bẫy Trang Chủ Trống ("Thử tìm kiếm để bắt đầu")**: Với tài khoản mới hoặc tắt lịch sử xem, F5 vô tác dụng. Bắt buộc click tab `Shorts` lướt 5-8s rồi click lại `Trang chủ` (hoặc gõ từ khóa tìm kiếm) để kích hoạt feed bung ra ~30 video.
   - **Bẫy Click Thẻ Quảng Cáo ("Được tài trợ" / "Sponsored")**: Tuyệt đối bỏ qua các card có chữ Được tài trợ. Bắt buộc tìm thẻ video thật có chứa `/watch?v=` và click vào.
   - **Xác Nhận Đang Phát Thật**: Chờ URL chuyển sang `**/watch*`, gửi phím `'k'` unpause nếu cần, duy trì xem 90 - 120 giây (gửi keep-alive heartbeat `/api/stats/watchtime` và nạp cookie AdSense).
   - **Nghiệm Thu Bằng CDP**: Để tránh timeout web fonts trên proxy 4G khi chụp ảnh màn hình, sử dụng trực tiếp CDP `Page.captureScreenshot` qua Playwright để chụp ngay trong lúc video đang phát.
2. **Google News (news.google.com)**:
   - Đồng bộ hóa sâu `GAPS` và `NID` cookie gắn với vị trí địa lý Việt Nam.
   - Lướt trang chủ, click mở 1 bài báo thật sự sang tab mới.
   - Đọc bài báo trong **45 - 60 giây**, mô phỏng cuộn trang tự nhiên (mỗi 6-10s cuộn chuột nhẹ 1 đoạn).
3. **Google Search (google.com)**:
   - Tìm kiếm 1 từ khóa ngẫu nhiên về tin tức, thời tiết, kinh tế, ẩm thực.
   - Dừng lại xem trang kết quả 10 - 15 giây trước khi đóng tab.

## 3. Quản Lý Trạng Thái & Vận Hành Bằng Cron
- Script canonical: `D:\Taadaa\GPM auto\scripts\cron_gpm_gmail_nurture.py`
- State file: `D:\Taadaa\runtime\kibe\cron-state\gpm_gmail_nurture_state.json`
- Chu kỳ: Mỗi tài khoản được dạo chơi nuôi định kỳ 1 lần sau mỗi 5 - 7 ngày. Cronjob `gpm-gmail-nurture-watchdog` chạy rải rác trong ngày lúc 09h, 11h, 13h, 15h, 17h, 19h, 21h.
