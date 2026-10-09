# Phân Tích Thực Nghiệm GemPhoneFarm vs Python Runner (Án Phạt Nhả Follow & Device Clustering)
Ngày ghi nhận: 14/09/2026

## 1. Bản Chất Của Hiện Tượng "0 Nick Tự Thoát Phạt Nhả Follow"
- **Dữ liệu thực tế đối soát:** 170/176 nick dính fail_streak >= 1 (bị phạt nhả follow) trong farm đều đã đăng > 5 video (trung bình 10.9 video/nick, nhiều nick 20-23 video).
- **Phản biện lý thuyết truyền miệng:**
  1. Lý thuyết "đăng video đều là follow được": **SAI**. Nick đăng 23 video vẫn dính streak 3 (bị giam 7 ngày).
  2. Lý thuyết "ngâm hết ngày cooldown tự mở": **SAI**. Sau 7 ngày, tài khoản vẫn ở trên con máy đó, IP đó, kịch bản cũ, bấm follow phát đầu tiên bị drop ngay lập tức.
  3. Lý thuyết "chỉ cần lướt feed thả tim dạo là tăng Trust Score gỡ phạt": **SAI**. ByteDance Security SDK đánh giá Anomaly Detection ở tầng thiết bị và cụm tương quan (Device Cluster), không cộng điểm cơ học theo lượt like.

## 2. Bí Mật Kỹ Thuật Đúc Rút Từ 856 Nodes GemPhoneFarm Của Ông Khoa
So sánh trực tiếp giữa file decrypted của GemPhoneFarm (`TIKTOK-FLOW-TÌM-KIẾM`, `TIKTOK-Nuoi-Tai-Khoan-Goc`, `TIKTIK-ĐĂNG-VIDEO`) và Python Runner:

| Đặc tính | GemPhoneFarm (Ông Khoa) | Python Runner (Code Cũ) | Đã Chuẩn Hóa Vào Python Runner |
|---|---|---|---|
| **Dwell Time ngâm Profile** | 5.8s – 12.5s (`5812, 12549 ms`) | 1.5s – 2.5s (quá vội) | Ngẫu nhiên `6.0s – 12.0s` trước khi tap Follow |
| **Delay sau khi Tap Follow** | 1.8s – 5.6s (`1814, 5654 ms`) | 1.5s cố định | Ngẫu nhiên `2.5s – 5.0s` |
| **Khoảng cách giữa 2 Follow** | 5.1s – 29.5s (`5142, 29521 ms`) | 1.0s – 5.0s | Ngẫu nhiên `8.0s – 25.0s` (cả Mode 1 và Mode 2) |
| **Tương tác Like Feed** | Random 20% – 50% theo tab | 8% cố định, tab khác 0-50% cứng | Following random 30-60%, Friends random 50-80% |
| **Tương tác Lưu (Bookmark)** | Có node tap `Lưu` / `Favorite` | Không có | Khi Like thành công, có 15-30% tap nút Lưu sau 0.8-1.8s |
| **Tần suất Upload Video** | 1 video/ngày | Chạy cả 2 phiên trong ca nuôi | Thu gọn: chỉ chạy ở Phiên 2 (`$SessionIndex -eq 2`) |
| **Phương thức phát sự kiện** | Android Accessibility Service | `adb shell input tap/swipe` | Tọa độ jitter tránh dx=0, random duration |

## 3. Tử Huyệt Của Lệnh ADB Input Trước ByteDance Security SDK (`libmetasec_ml.so`)
Qua phân tích sâu từ GPT-5.6 Sol High Reasoning:
1. **Lực nhấn (Pressure):**
   - Ngón tay thật: biến thiên liên tục (`0.12 -> 0.45 -> 0.8 -> 0.2`).
   - Lệnh ADB: luôn trả về `pressure = 1.000` cố định 100% (phương sai variance = 0).
2. **Diện tích tiếp xúc (Touch Size / Major / Minor):**
   - Ngón tay thật: `major = 7.4px, minor = 5.2px`.
   - Lệnh ADB: `size = 0, major = 0, minor = 0`.
3. **Quỹ đạo vuốt tuyến tính (Linear Trajectory dx = 0):**
   - Quẹt thẳng tắp dx = 0 với vận tốc đều đặn (velocity variance = 0, jerk = 0) là signature rõ rệt của bot.
   - Khắc phục: Phải có độ lệch tự nhiên ngón tay cái và biến thiên thời gian vuốt (550 - 750ms).
4. **Device Clustering 8 nick/máy:**
   - 8 tài khoản luân phiên trên cùng 1 Hardware ID (Exynos 8890, Mali-T880, cùng SensorList, cùng display density 560dpi, cùng gateway 4G) tạo thành cụm rủi ro cao (High Scrutiny Bucket).
   - TikTok không ban nick mà âm thầm áp dụng cơ chế Silent Rollback (Optimistic UI + Async Backend Drop).
