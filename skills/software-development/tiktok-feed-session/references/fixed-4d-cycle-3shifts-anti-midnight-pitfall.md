# Chu Kỳ Nuôi 4 Ngày Chuẩn Hóa (Parity 96h, Bỏ Hoàn Toàn Ca 0h Đêm)

Cập nhật chính thức: Áp dụng từ 11/10/2026 (`BASE_ORDINAL = 739900`).

## 1. Lịch 3 Ca x 2 Phiên / Ngày
Toàn bộ hệ thống Phone Farm nuôi TikTok chỉ chạy 3 Ca ban ngày và tối. BỎ HOÀN TOÀN CA 00:00 VÀ 01:30 ĐÊM:
- **Ca 1 (Sáng):** Phiên 1 lúc `06:00` (Feed only), Phiên 2 lúc `08:00` (+ Upload/Follow hook).
- **Ca 2 (Trưa):** Phiên 1 lúc `12:00` (Feed only), Phiên 2 lúc `14:00` (+ Upload/Follow hook).
- **Ca 3 (Tối):**  Phiên 1 lúc `18:00` (Feed only), Phiên 2 lúc `20:00` (+ Upload/Follow hook).
- **Dead Zone ban đêm (`21:30` -> `05:59`):** 
  - Toàn bộ 80 máy nghỉ ngơi hoàn toàn, màn hình tắt, giải phóng lock để hạ nhiệt pin Samsung S7 và bảo vệ kết nối USB.
  - Chạy dọn cache TikTok (`end-of-day-clear-tiktok-cache`) trong khung `03:00` - `04:30`.
  - TUYỆT ĐỐI KHÔNG CÓ BẤT KỲ CA FEED NÀO VÀO BAN ĐÊM.

## 2. Phân Bổ Chu Kỳ 4 Ngày (Parity Cố Định 96h)
- **Day 0 (Ngày 1):** Ca 1 (Row 1) - Ca 2 (Row 3) - Ca 3 (Row 5).
- **Day 1 (Ngày 2):** Ca 1 (Row 2) - Ca 2 (Row 4) - Ca 3 (Row 6).
- **Day 2 (Ngày 3):** Ca 1 (Row 7) - Ca 2 (Row 8) - Ca 3 (Dưỡng sinh Row 3/4 pure feed).
- **Day 3 (Ngày 4):** Dưỡng sinh xả tải toàn farm (pure feed / nghỉ ngơi).

## 3. Cạm Bẫy Trí Nhớ Cũ & Tài Liệu Cũ
- **Không có chuyện Row 8 chạy rạng sáng 01:30:** Lịch cũ (ngày chẵn/lẻ 4 ca có ca 0h) đã bị xóa bỏ hoàn toàn. Row 8 chạy vào Ca 2 (Trưa) của Day 2 trong chu kỳ 4 ngày.
- **Không chạy bù feed đêm:** Khi một Row bị văng nhiều máy trong ngày, dung sai chu kỳ 4d (starve 96h-108h) bảo vệ nick an toàn. Ép chạy bù vào 01h-03h đêm sẽ phá nát thời gian nghỉ, đè vào lịch dọn cache 03h và đè vào Ca 1 sáng lúc 06h.
