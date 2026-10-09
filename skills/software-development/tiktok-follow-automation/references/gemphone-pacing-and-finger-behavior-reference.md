# GemPhone Pacing, Dwell Time & Touch Naturalization Reference

## 1. Bối cảnh thực nghiệm: Tại sao 170/176 nick đăng >5 video vẫn bị nhả follow?
- Đối soát thực tế giữa `taikhoan_run_safe.xlsx` và 176 file `follow_state_*.json`:
  - 170/176 nick dính phạt follow (`fail_streak >= 1`) đều đã đăng trên 5 video (trung bình 10.9 video/nick, nhiều nick 20-23 video).
  - Lời khuyên truyền miệng "nuôi đăng video đều là follow được" không đủ để giải quyết bài toán nếu nhịp độ tương tác và cấu trúc thiết bị bị nhận diện bot farm.
  - Cả GPT-5.6 Sol và Claude Opus khi phân tích đều chỉ ra: Tầng Risk Control của TikTok kích hoạt **Optimistic UI + Async Backend Silent Rollback** chủ yếu dựa trên:
    1. **Device Clustering**: Nhiều tài khoản (8 acc/máy) chung phần cứng/ROM/Android ID.
    2. **Hành vi thao tác quá vội (Timing & Dwell Time Anomaly)**: Vừa load xong Activity/Profile là tap ngay, khoảng cách giữa các lượt follow quá ngắn.
    3. **Độ thẳng cơ học của thao tác vuốt (Zero-entropy Swiping)**: Vuốt thẳng tắp `dx = 0` với cùng vận tốc và tọa độ pixel dập khuôn.

## 2. Mổ xẻ thông số kỹ thuật từ 3 bộ workflow GemPhoneFarm gốc của ông Khoa
Trích xuất từ:
- `TIKTOK-FLOW-TÌM-KIẾM-Thành-đạt_decrypted.json` (389 nodes)
- `TIKTOK-Nuoi-Tai-Khoan-Goc_decrypted.json` (205 nodes)
- `TIKTIK-ĐĂNG-VIDEO-Đạt_Decrypted.gemphonefarm` (64 nodes)

### A. Thời gian ngâm Profile (Dwell Time)
- GemPhone Node delay: `5812, 12549 ms`.
- Khi search ra nick hoặc mở profile mục tiêu, **ngâm từ 5.8s đến 12.5s** rồi mới bấm nút Follow.
- Chuẩn hóa sang Python runner: `time.sleep(random.uniform(6.0, 12.0))`.

### B. Thời gian chờ Server ghi nhận sau khi Tap Follow
- GemPhone Node delay: `1814, 5654 ms`.
- Không thoát profile ngay lập tức sau khi bấm follow; chờ 2.5s - 5.0s để server TikTok xử lý.
- Chuẩn hóa sang Python runner: `time.sleep(random.uniform(2.5, 5.0))`.

### C. Khoảng cách nghỉ giữa 2 lần Follow
- GemPhone Node `rf10473`: `5142, 29521 ms` (5.1s đến tận 29.5s).
- Chuẩn hóa sang Python runner: `random.uniform(8.0, 25.0)`.

### D. Ngẫu nhiên hóa tỷ lệ thả tim feed 3 tab
- Trong `TIKTOK-Nuoi-Tai-Khoan-Goc`, biến `%_Tim` biến thiên ngẫu nhiên theo phiên.
- Chuẩn hóa sang Python runner (`_feed_like_rates` khi không có config cứng):
  - Tab Following (Đang follow): ngẫu nhiên [30%, 60%].
  - Tab Friends (Bạn bè): ngẫu nhiên [50%, 80%].
  - Tab For You (Đề xuất): 8%.

### E. Quỹ đạo vuốt tự nhiên (Natural Finger Drift)
- Tránh bẫy `start_x == end_x` (dx = 0) dập khuôn cơ học.
- Giữ an toàn tuyệt đối cho màn hình 1080x1920:
  - `start_x`: 470 - 520 px (chính giữa tâm màn hình).
  - `end_x`: lệch nhẹ tự nhiên $\pm 15 \sim 25\text{ px}$ (độ cong ngón cái), xa ngưỡng 150px kích hoạt lật màn Camera/Profile.
  - `start_y`: 1350 - 1400 px (cách xa khung comment ở đáy $Y \ge 1500$).
  - `end_y`: 450 - 500 px.
  - `duration_ms`: 520 - 750 ms.
