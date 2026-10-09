# Kiến trúc Nuôi TikTok Farm: 4 Ca x 2 Phiên (Chốt 09/09/2026)

## 1. Phân bổ Ca & Mốc Giờ (4 Ca trải đều 6 tiếng)
- **Ca 1 (Sáng):** Bắt đầu lúc `06:00` (Phiên 1: 06:00 - 07:30, Phiên 2: 07:30 - 10:00).
- **Ca 2 (Chiều):** Bắt đầu lúc `12:00` (Phiên 1: 12:00 - 13:30, Phiên 2: 13:30 - 16:00).
- **Ca 3 (Tối):** Bắt đầu lúc `18:00` (Phiên 1: 18:00 - 19:30, Phiên 2: 19:30 - 22:00).
- **Ca 4 (Đêm):** Bắt đầu lúc `00:00` (Phiên 1: 00:00 - 01:15, Phiên 2: 01:15 - 03:00).
- **Khung nghỉ sâu đêm:** `03:00 - 06:00` nhường giờ cho dọn cache (04:00) và các batch bảo trì.

## 2. Quy hoạch Hàng (Row) & Tài khoản (Max 8 acc/máy)
- **Ngày Lẻ (Lane B):** Row 1 (Ca 1), Row 3 (Ca 2), Row 5 (Ca 3), Row 7 (Ca 4).
- **Ngày Chẵn (Lane A):** Row 2 (Ca 1), Row 4 (Ca 2), Row 6 (Ca 3), Row 8 (Ca 4).
- Mỗi tài khoản chạy đúng 1 Ca/ngày (2 Phiên lướt), cách 1 ngày chạy lại.

## 3. Cấu trúc Phiên & Hook hoàn tất
- **Mỗi ca gồm 2 Phiên:**
  - **Phiên 1:** Lướt feed tương tác nhẹ, tạo telemetry hoạt động (~30-35p), sau đó máy nghỉ `pair_gap` (35-60p).
  - **Phiên 2 (Phiên cuối ca):** Lướt feed + kích hoạt **Upload Hook (Đăng Video)** & **Follow Hook**.
- **Hook Đăng Video:** BẮT BUỘC gate tại `_effective_session_index(config) == 2` (không còn là phiên 3).
- **Hook Follow:**
  - Mỗi phiên chạy ~15 - 18 lượt follow (`budget_per_session_min: 15`, `max: 18`, `default: 18`).
  - Đảm bảo 2 phiên đạt trần an toàn `35 follow/ngày`.
  - Gate an toàn: Nick phải có `video_count >= 5` mới được chạy follow hook.

## 4. Watchdog & Báo cáo (`feed_session_watchdog.py`)
- `SESSION_WINDOWS` định nghĩa 8 cửa sổ tương ứng 4 ca x 2 phiên.
- Báo cáo ghi nhận nhãn `(Đăng video)` cho tất cả các Phiên 2 của cả 4 Ca.
