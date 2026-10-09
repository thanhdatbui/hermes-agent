# Thống nhất điều kiện Follow (Tự Nhiên & Chéo) và Lọc Báo Cáo Đối Soát Watchdog

User chốt ngày 2026-10-02:

## 1. Single Source of Truth cho Mọi Hành Vi Follow (Tự Nhiên Lẫn Chéo)
- **Vấn đề trước đây:** Follow chéo đã có Dual Gate (chặn khi tuổi nick < 21 ngày hoặc video < 6), nhưng lướt feed (Follow tự nhiên) chỉ check mỗi video_count >= 6 mà bỏ quên tuổi nick. Kết quả là nick 16 ngày tuổi vẫn bấm follow 3 lượt trên feed, bị TikTok hủy và watchdog báo lệch web.
- **Quy tắc bất biến:** CẤM TUYỆT ĐỐI duy trì 2 bộ quy tắc riêng rẽ giữa Follow Tự Nhiên (lướt feed) và Follow Chéo (hook sau feed). Follow tự nhiên BẮT BUỘC tuân theo cùng điều kiện của follow chéo:
  1. **Ngày dưỡng sinh (Organic Rest):** Khóa cả 2 (`_follow_rate = 0`, skip follow hook với lý do `organic-rest-day-pure-feed`).
  2. **Bị Cooldown do nhả follow (`is_account_in_follow_cooldown`):** Khóa cả 2 cho tới khi hết hạn.
  3. **Dual Gate (Tuổi nick & Số video):** BẮT BUỘC `account_age_days >= 21` VÀ `video_count >= 6` (nếu không có cột ngày tạo thì `video_count >= 10`). Nick chưa đủ 21 ngày tuổi hoặc chưa đủ 6 video -> Khóa hoàn toàn follow tự nhiên (`_follow_rate = 0`, `_maybe_follow_video` skip) VÀ skip follow hook ngay từ đầu với lý do chuẩn (`under-21-days-follow-disabled` hoặc `under-6-videos-follow-disabled`), tuyệt đối không gọi subprocess vô ích.

## 2. Kỷ Luật Đối Soát Báo Cáo Watchdog (Không Báo Nick Không Lệch)
- **Vấn đề trước đây:** Watchdog in ra cả các nick có `diff == 0` (KHỚP / chênh lệch +0) vào bảng "Đối soát TikTok Web", gây loãng report.
- **Quy tắc:**
  - Trong bảng "Đối soát TikTok Web" của watchdog report: Nick nào KHÔNG lệch (`diff == 0` / web tăng khớp 100% so với script báo) TUYỆT ĐỐI CẤM in vào danh sách chi tiết.
  - CHỈ in ra các nick thực sự có độ lệch (`diff != 0`) hoặc gặp lỗi snapshot/unproven để đảm bảo report tinh gọn, đúng trọng tâm.
