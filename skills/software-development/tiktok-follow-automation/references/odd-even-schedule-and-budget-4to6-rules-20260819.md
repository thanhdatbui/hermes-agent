# Quy Tắc Vận Hành Lịch Chẵn/Lẻ (2 Ca Follow/Ngày), Budget 4-6 & Timeout Golden Window (19/08/2026)

## 1. Lịch Vận Hành Chẵn / Lẻ Chốt Ngày 19/08/2026
- **Chiến lược phân tầng (Tiering):**
  - **Tier 1 (Mũi nhọn - Row 1 & Row 2):** Đã có 8 - 12 video -> Đủ điều kiện follow chéo và đăng video mở giỏ hàng TikTok Shop.
  - **Tier 2 (Gối đầu & Hậu cần - Row 3, 4, 5, 6):** Hiện 0 video -> **CẤM FOLLOW 100% (`zero-video-follow-disabled`)**. Chỉ chạy lướt Feed làm ấm (warm-up) ở Ca Trưa.
- **Bảng phân bổ 3 ca trong ngày:**
  - **NGÀY LẺ (1, 3, 5, 7...):**
    - Ca 1 (Sáng 06:00, Jitter ±25p): **Row 1** (Lướt Feed + Follow Cữ 1: 4-6 nick).
    - Ca 2 (Trưa 12:30): **Row 3** (Lướt nuôi + Chuẩn bị render/upload video) & **Row 5** (Lướt nhẹ warm-up). (0 follow).
    - Ca 3 (Tối 19:00, Jitter ±25p): **Row 1** (Lướt Feed + Follow Cữ 2: 4-6 nick).
    - *Tổng kết Row 1:* Ăn trọn 2 ca x 3 phiên, follow 8 - 12 nick/ngày, đăng 2 video/ngày, sau đó nghỉ trọn ngày Chẵn.
  - **NGÀY CHẴN (2, 4, 6, 8...):**
    - Ca 1 (Sáng 06:00, Jitter ±25p): **Row 2** (Lướt Feed + Follow Cữ 1: 4-6 nick).
    - Ca 2 (Trưa 12:30): **Row 4** & **Row 6** (Lướt nhẹ warm-up, 0 follow).
    - Ca 3 (Tối 19:00, Jitter ±25p): **Row 2** (Lướt Feed + Follow Cữ 2: 4-6 nick).
    - *Tổng kết Row 2:* Ăn trọn 2 ca x 3 phiên, follow 8 - 12 nick/ngày, đăng 2 video/ngày, sau đó nghỉ trọn ngày Lẻ.

## 2. Quy Trình Vét Cạn List & Gối Đầu 2 Giai Đoạn
- **Giai đoạn 1 (Hiện tại: ~200 nick):** Row 1 & Row 2 tập trung follow quét hết danh sách nick hiện có trong farm đến khi cạn (`exhausted`).
- **Giai đoạn 2 (Mở rộng tệp):** Kích hoạt Render & Upload video cho Row 3, 4, 5, 6 lên $\ge 8$ video -> Mở khóa tính năng follow cho các row này để mở rộng bể follow nội bộ.

## 3. Điều Chỉnh Budget Follow & Jitter
- **Budget Follow mỗi phiên:** Hạ từ 5-10 xuống **4 – 6 follow/phiên** (min: 4, max: 6) trong `follow_runner/config.example.yaml`.
  - Phù hợp khi 1 ngày chạy 2 ca x 3 phiên, giúp tổng follow tích lũy trong ngày rơi vào vùng an toàn 8 - 12 follow, không bị TikTok quét spam rate-limit.
- **Jitter liên tục $\pm 25$ phút (`range(-25, 26)`):** Phân tán thời gian bật app từ 05:35 đến 06:25, triệt tiêu 100% hiện tượng spike lưu lượng mạng diện rộng lúc 09:45.

## 4. Phân Định Rạch Ròi: "Giữ Nguyên Hiện Trường" vs "Nhả Follow"
- **Lỗi Giao Diện / Kẹt UI / Manual Review (Popup lạ, kẹt phím, không load feed):**
  - **BẮT BUỘC GIỮ NGUYÊN HIỆN TRƯỜNG:** Không đóng app, không về Home để phục vụ AI Recovery và debug lỗi.
- **Sự cố Nhả Follow (`FOLLOW_FAILED`):**
  - Khi TikTok quét nhả follow -> **Ngắt phiên ngay ➔ Đóng app, clear recents và về Home** để bảo vệ tài khoản.
  - Ghi nhận `follow_failed = True` và `follow_failed_date = "YYYY-MM-DD"` cô lập cho RIÊNG nick đó (`follow_state_<máy>_row_<index>.json`).
- **Tự động phục hồi khi sang ngày mới:**
  - Hàm `_roll_day()` trong `follow_state.py` tự động reset `follow_failed = False` và xóa `follow_failed_date` khi bước sang ngày mới để nick được tiếp tục follow bình thường.

## 5. Nâng Ngưỡng Feed Timeout 900s (15 Phút) & Force-Stop Khi Hết Giờ
- **Nâng `feed_timeout_seconds` lên 900s (15 phút) đồng bộ toàn farm:**
  - Đồng bộ chuẩn 15 phút (900s) cho cả 3 khâu: Lướt Feed, Follow Hook, và Upload Video.
  - 15 phút tạo "Khung giờ vàng" thoải mái cho AI Auto-Recovery đọc ảnh vision, gọi model audit và gỡ popup trọn vẹn mà không lo bị ngắt giữa chừng.
- **Xử lý Timeout Hết Giờ (>15 phút):**
  - Trong 15 phút: Giữ nguyên hiện trường cho AI Recovery sửa.
  - Khi tiến trình chạm ngưỡng Timeout (>15 phút) mà không tự gỡ được: BẮT BUỘC tự động `am force-stop com.ss.android.ugc.trill` và bấm `HOME (keyevent 3)`.
  - Tuyệt đối không để app ngâm treo màn hình qua đêm vì ngâm treo app là nguyên nhân trực tiếp khiến TikTok gắn cờ bot và nhả follow ở các phiên sau.
