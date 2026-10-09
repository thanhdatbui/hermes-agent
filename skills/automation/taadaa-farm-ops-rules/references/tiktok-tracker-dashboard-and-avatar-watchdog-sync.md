# TikTok Farm Account Tracker & Avatar Watchdog Sync Architecture

## 1. Context & Architecture Overview
- Farm TikTok có Web Dashboard (`http://localhost:1905`, port 1905) và crawler định kỳ `daily-tiktok-farm-tracker` (`cron_tiktok_daily_tracker.py` -> `D:/Taadaa/tools/tiktok_account_tracker.py`).
- Cơ sở dữ liệu SQLite lưu trữ trung tâm: `D:/Taadaa/data/tiktok_tracker.db` (bảng `snapshots` và `farm_account_info`).
- Watchdog ca tối: `post_evening_avatar_watchdog.py` (chạy cuốn chiếu từ 20:15/21:00 đến 23:45 trên host Kibe/Admin) để up avatar cho các nick chưa có avatar.

## 2. Pitfalls & Anti-Patterns Learned

### Pitfall 1: Lệch pha giữa Web Dashboard SQLite và Ca chạy Avatar
- **Triệu chứng:** Watchdog ca tối up avatar thành công hàng chục máy, nhưng báo cáo cuối ca (sau 23:30) vẫn báo số lượng cũ (thiếu avatar hàng loạt) và tiếp tục spawn lặp lại vào tối hôm sau.
- **Nguyên nhân gốc rễ:**
  - `tiktok_tracker.db` chỉ được cron `daily-tiktok-farm-tracker` quét 1 lần/ngày lúc **07:00 sáng**.
  - Sau khi batch upload avatar ca tối hoàn tất trên máy thật (21:00-23:45), không có cơ chế re-scan crawler TikTok.
  - Khi watchdog truy vấn `tiktok_tracker.db` để báo cáo, nó đọc phải snapshot cũ từ 7h sáng hôm trước.
- **Quy tắc thiết kế đúng:**
  - Nguồn Source of Truth để gate avatar trên thực tế TikTok là Crawler (`has_avatar` bóc tách từ HTML).
  - Sau ca tối, watchdog BẮT BUỘC phải kích hoạt re-scan crawler cho các máy vừa up thành công trước khi xuất báo cáo tổng kết:
    `python D:/Taadaa/tools/tiktok_account_tracker.py --machines <danh_sách_máy_vừa_up> --workers 10`
  - Báo cáo tổng kết sẽ đọc snapshot mới nhất vừa quét, đồng bộ trạng thái lên Web Dashboard 1905 và gửi Telegram Farm Alert.

### Pitfall 2: Query SQLite gộp chung Farm thiếu lọc `host_id`
- **Triệu chứng:** Tik 7 trên Kibe bị báo có tới 132 máy (trong khi mỗi host tối đa 80 máy), danh sách máy bắt Kibe chạy cả dải 201..224 của Admin.
- **Nguyên nhân:**
  - `farm_account_info` lưu tập trung cả tài khoản Kibe (máy 1..80) và Admin (máy 201..280).
  - Query cũ: `SELECT m.may ... WHERE m.tik = ?` mà thiếu điều kiện host hoặc dải máy.
- **Quy tắc xử lý:**
  - Luôn filter theo host context:
    - Kibe: `m.may BETWEEN 1 AND 80` hoặc `m.host_id = 'kibe'`
    - Admin: `m.may BETWEEN 201 AND 280` hoặc `m.host_id = 'admin'`

### Pitfall 3: Lệch khung giờ Cron Schedule khiến mất báo cáo tổng kết
- **Triệu chứng:** Batch upload kết thúc lúc 23:56 nhưng Farm Alert không nhận được tin nhắn tổng kết.
- **Nguyên nhân:**
  - Logic script có `is_after_evening_window` cho phép tổng kết từ 23:45 đến 04:00 sáng.
  - Nhưng cấu hình cron expr chỉ khai báo: `*/5 20,21,22,23 * * *`. Lần tick cuối lúc 23:55 (batch vẫn đang chạy dở). Qua 00:00 cron không còn tick nào nữa.
- **Quy tắc xử lý:**
  - Cron schedule cho các watchdog có phase kết thúc sau nửa đêm BẮT BUỘC phải bao phủ cả các giờ rạng sáng:
    `*/5 20,21,22,23,0,1,2,3 * * *`
