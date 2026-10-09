# Kiến trúc Nuôi TikTok 8 Acc/Máy (4 Ca x 2 Phiên) & Chiến lược Giảm nhiệt Farm

## 1. Bối cảnh & Động lực Chuyển đổi (09/09/2026)
- **Cấu hình cũ (3 ca x 3 phiên = 9 phiên/máy):** Nuôi 6 acc/máy (Row 1-6). Mỗi ca 3 phiên kéo dài ~5 tiếng. Máy chạy liên tục ban ngày, thiếu khung giờ tản nhiệt và chạm trần tải phần cứng nếu mở rộng lên 8 acc.
- **Giới hạn thuật toán TikTok:**
  - TikTok tính quota hành vi (follow, like, action) theo Rolling 24h / Daily session, KHÔNG có cơ chế cộng dồn khi nghỉ cách ngày.
  - Nghỉ 2 ngày rồi dồn follow 35 cái/ngày dễ chạm trần action block / shadow-unfollow hơn là chạy đều đặn với volume vừa phải.
  - Người dùng thật hoạt động rải rác cả đêm (00:00 - 02:00), chia ca đêm là hành vi tự nhiên.

## 2. Kiến trúc 4 Ca x 2 Phiên (8 Acc/Máy: Row 1-8)
- **Tần suất:** 2 phiên/acc/ca (Phiên 1 lướt warm-up ~30-35p, Phiên 2 lướt + hook Follow/Upload ~30-35p).
- **Tổng thời gian chạy/ca:** ~1h30 - 2h (tiết kiệm hơn hẳn mức ~5 tiếng của 3 phiên).
- **Phân bổ LANES (Ngày Chẵn / Lẻ):**
  - **Ngày Lẻ (Lane B):** Row 1 (Ca 1), Row 3 (Ca 2), Row 5 (Ca 3), Row 7 (Ca 4)
  - **Ngày Chẵn (Lane A):** Row 2 (Ca 1), Row 4 (Ca 2), Row 6 (Ca 3), Row 8 (Ca 4)

## 3. Timeline 4 Ca Rải đều (06:00 đến 02:00)
- **Ca 1 (06:00):**
  - Phiên 1: `06:00 - 07:30`
  - Phiên 2: `07:30 - 10:00`
  - *Nghỉ tản nhiệt / Deep Sleep:* `10:00 - 12:00` (2 tiếng)
- **Ca 2 (12:00):**
  - Phiên 1: `12:00 - 13:30`
  - Phiên 2: `13:30 - 16:00`
  - *Nghỉ tản nhiệt / Deep Sleep:* `16:00 - 18:00` (2 tiếng)
- **Ca 3 (18:00):**
  - Phiên 1: `18:00 - 19:30`
  - Phiên 2: `19:30 - 22:00`
  - *Nghỉ tản nhiệt / Deep Sleep:* `22:00 - 00:00` (2 tiếng)
- **Ca 4 (00:00):**
  - Phiên 1: `00:00 - 01:15`
  - Phiên 2: `01:15 - 03:00`
  - *Nghỉ sâu ban đêm & bảo trì farm:* `03:00 - 06:00` (3 tiếng). Khung giờ này nhường tài nguyên cho `end-of-day-clear-tiktok-cache` (04:00) và hạ nhiệt toàn dàn.

## 4. Tương thích với các Cronjob Ban đêm
- Các job tạo đàn (Reg TikTok, Up Avatar) chỉ chạy tạm thời ở giai đoạn đầu. Khi máy đã đủ 8 acc (đến Row 8) và full avatar, các job này tự động dừng/nhàn rỗi.
- Job dọn cache TikTok (`end-of-day-clear-tiktok-cache`) chạy lúc 04:00 sáng nằm trọn vẹn trong khoảng nghỉ sâu (03:00 - 06:00), không tranh chấp device lock với Ca 4.

## 5. Lưu ý Kỹ thuật khi triển khai Tắt màn hình khi Idle
- Giữa các phiên và giữa các ca, máy phải được tắt màn hình để chống nóng máy, phồng pin và burn-in màn AMOLED.
- **Trước khi tắt:** Phải inspect `dumpsys display | grep mScreenState` (hoặc tương đương). Nếu màn hình đang `ON` mới gửi `input keyevent 26` (Power), tuyệt đối không gửi mù gây bật sáng màn hình đang tắt.
- **Khi vào phiên mới:** Gửi `input keyevent 224` (Wakeup) + Swipe unlock trước khi gọi package TikTok.
