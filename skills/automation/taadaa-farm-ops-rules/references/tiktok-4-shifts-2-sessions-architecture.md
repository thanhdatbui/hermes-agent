# Quy Chuẩn Kiến Trúc Vận Hành Nuôi TikTok Farm: 4 Ca x 2 Phiên (Chốt 09/09/2026)

## 1. Phân Bổ Ca & Mốc Giờ Vận Hành (4 Ca trải đều 6 tiếng)
- **Ca 1 (Sáng):** Bắt đầu `06:00` (Phiên 1: 06:00 - 07:30, Phiên 2: 07:30 - 10:00).
- **Ca 2 (Chiều):** Bắt đầu `12:00` (Phiên 1: 12:00 - 13:30, Phiên 2: 13:30 - 16:00).
- **Ca 3 (Tối):** Bắt đầu `18:00` (Phiên 1: 18:00 - 19:30, Phiên 2: 19:30 - 22:00).
- **Ca 4 (Đêm):** Bắt đầu `00:00` (Phiên 1: 00:00 - 01:15, Phiên 2: 01:15 - 03:00).
- **Khoảng Nghỉ Sâu Đêm:** `03:00 - 06:00` (toàn bộ máy nghỉ ngơi, nhường slot chạy cron dọn cache TikTok 04:00 và bảo trì).

## 2. Quy Hoạch Hàng Tài Khoản (Row) — Tối Đa 8 Acc / Máy
- **Ngày Lẻ (Lane B):** Row 1 (Ca 1), Row 3 (Ca 2), Row 5 (Ca 3), Row 7 (Ca 4).
- **Ngày Chẵn (Lane A):** Row 2 (Ca 1), Row 4 (Ca 2), Row 6 (Ca 3), Row 8 (Ca 4).
- Mỗi tài khoản chạy đúng 1 Ca/ngày (gồm 2 Phiên lướt feed), chạy cách ngày (2 ngày 1 lần).

## 3. Cấu Trúc Phiên & Hook Tác Vụ
- **Phiên 1:** Lướt feed tương tác nhẹ, tạo telemetry tự nhiên (~30-35p), sau đó máy tự về Home/tắt màn nghỉ ngơi theo `pair_gap` (35-60p).
- **Phiên 2 (Phiên Cuối Ca):** Lướt feed + kích hoạt:
  - **Hook Đăng Video (Upload Hook):** Đã dời sang Phiên 2 (Gate: `_effective_session_index(config) == 2`).
  - **Hook Follow:** Kích hoạt với quota tăng lên `15 - 18 lượt follow/phiên` (để 2 phiên đạt đủ trần `35 follow/ngày`).
  - Gate an toàn follow: Tài khoản phải có `video_count >= 5` mới được chạy follow hook.

## 4. Đồng Bộ Watchdog Báo Cáo (`feed_session_watchdog.py`)
- Cập nhật 8 Time Windows tương ứng cho 4 ca x 2 phiên.
- Dán nhãn `(Đăng video)` cho toàn bộ Phiên 2 của cả 4 Ca.
