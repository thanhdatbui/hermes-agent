# Đánh giá Hiệu năng & Đo đạc Lỗi Thuần Hạ tầng: 30 Workers vs 40 Workers (2026-08-25)

## 1. Nguyên tắc Đánh giá Hạ tầng (User Rule)
- Khi đánh giá lỗi do tăng tải worker (từ 30 lên 40 luồng song song), **BẮT BUỘC chỉ đo đạc và thống kê lỗi thuần túy hạ tầng/phần cứng**:
  - `ADB Transport Lost` / `Broken pipe` / `Closed transport`.
  - `Device Lock Conflict` (tranh chấp/kẹt lock giữa các tiến trình).
  - `Corrupted Image Capture` (lỗi truyền dữ liệu ảnh chụp màn hình qua ADB).
  - `ADB Daemon (5037) Socket / Port Crash`.
  - `Device Offline` / Mất kết nối USB.
- **TUYỆT ĐỐI KHÔNG gộp các lỗi ứng dụng / script** (như popup TikTok mới, lỗi UI layout, ATX session chưa khởi động, hay lỗi login/OTP) vào báo cáo quá tải hạ tầng, vì các lỗi này do logic script hoặc phía TikTok, không liên quan đến khả năng chịu tải của máy chủ và USB bus.

## 2. Số liệu Thực nghiệm trên Farm 160 Máy (Host Kibe)
- **Giai đoạn 30 Workers (667 lượt máy):**
  - ADB Transport Lost: 2 ca.
  - Device Lock Conflict: 5 ca.
  - Corrupted Image Capture: 2 ca.
- **Giai đoạn 40 Workers (173 lượt máy):**
  - ADB Transport Lost: 0 ca.
  - Device Lock Conflict: 0 ca.
  - Corrupted Image Capture: 0 ca.

## 3. Cơ chế Bảo vệ Giúp 40 Workers Hoạt động Ổn định
- **Stagger Random 2.000 – 8.000 ms:** Phân tán đỉnh xung kích (peak burst traffic) khi khởi động từng worker, giúp ADB Server 5037 không bị quá tải socket.
- **Tốc độ giải phóng hàng đợi:** 40 workers giúp dọn dẹp các máy xong sớm hơn, giảm thời gian ngâm hàng đợi và triệt tiêu tình trạng giữ lock quá hạn deadline.
