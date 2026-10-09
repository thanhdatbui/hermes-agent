# Quy Tắc Báo Cáo Telegram Cronjob Gộp Toàn Farm (Kibe + Admin)

## 1. Cấm Raw HTML Tags
- Tuyệt đối CẤM in raw HTML tag (`<b>`, `</b>`, `<i>`) trong stdout của watchdog/cron.
- Telegram delivery của Hermes khi nhận stdout từ job `no_agent=true` không parse tag thô, dẫn đến lộ nguyên chữ `<b>...</b>` gây mất thẩm mỹ. Dùng text thuần có phân cấp hoặc ký tự bullet `•`, `🏢 【...】`.

## 2. Cấu Trúc Khối Đa Cụm (Dual-Cluster)
- Header tổng quát toàn farm trước:
  ```text
  ⏰ [FARM REPORT][TOÀN FARM] BÁO CÁO UP AVATAR: HẾT KHUNG GIỜ
  • Thời gian: HH:MM:SS DD/MM/YYYY
  • Trạng thái: Hết khung giờ ca tối (sau 23:30) — Đã có: X/Y acc (Z%), còn N máy chưa up
  ```
- Phân khối 2 cụm riêng biệt:
  * `🏢 【FARM KIBE - MÁY 1-80】: Đã có X/Y (Z%), còn N máy`
  * `🏢 【FARM ADMIN - MÁY 201-280】: Đã có X/Y (Z%), còn N máy`

## 3. Quy Tắc Gom Gọn & Chống Rác (Legibility Invariants)
- **Tik hoàn tất 100%:** Gom vào 1 dòng duy nhất cuối cụm (`  • Hoàn tất 100%: Tik 3, Tik 5, Tik 8...`). CẤM in từng dòng riêng lẻ cho các Tik đã 100%.
- **Tik trống không có tài khoản (`total == 0`):** Ẩn hoàn toàn khỏi báo cáo, tuyệt đối không in `chưa gán nick (0/80 acc)` gây loãng.
- **Preview danh sách máy tồn đọng/lỗi:**
  * Giới hạn tối đa 10 máy: `", ".join(map(str, un[:10]))`.
  * Có dấu cách sau dấu phẩy `(201, 202, 205...)`, nếu vượt quá 10 máy thì thêm hậu tố `... (+N)`. CẤM dính liền số không khoảng trắng.
