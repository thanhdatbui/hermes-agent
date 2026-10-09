# Dual-Cluster Farm Reporting Reference (Kibe Master + Admin Thin Worker)

## Kiến trúc Quản lý Tập trung
- **Master Node (Kibe):** Chạy bot Telegram Hermes, toàn bộ cron runner, watchdog, GPM, SQLite `tiktok_tracker.db`.
- **Worker Node (Admin):** Kết nối 80 điện thoại qua USB Hub, chia sẻ ADB server qua mạng LAN `192.168.110.119:5037`.

## Quy tắc Định dạng Báo cáo Gộp [TOÀN FARM]
Thay vì gửi các tin nhắn phân mảnh riêng rẽ từ từng máy làm loãng kênh chat:
1. **Header chung:** Bắt buộc dùng `[TOÀN FARM]` (hoặc tổng hợp chung ở đầu).
2. **Phân tách 2 khối cụm rõ ràng:**
   - Cụm Kibe: `🏢 【FARM KIBE - MÁY 1-80】`
   - Cụm Admin: `🏢 【FARM ADMIN - MÁY 201-280】`
3. **Áp dụng đồng nhất:**
   - **Nuôi acc (`feed_session_watchdog.py`):** Gom kết quả feed, tim, follow, upload của cả 2 runtime (`D:/Taadaa/runtime/kibe` và `D:/Taadaa/runtime/admin`).
   - **Avatar (`post_evening_avatar_watchdog.py`):** Lấy danh sách máy và trạng thái `has_avatar` từ SQLite database `tiktok_tracker.db` theo 2 dải máy (`may < 200` và `may >= 200`), hiển thị chi tiết tiến độ từng Tik theo từng cụm.

## Quy tắc Đồng bộ 3 Điểm cho Scripts Cron
Mọi thay đổi trên script cron/watchdog phải luôn được đồng bộ nguyên tử tới 3 nơi:
1. Local AppData: `C:/Users/Kibe/AppData/Local/hermes/scripts/<script>.py`
2. Git Deploy: `D:/Taadaa/Hermes/deploy/hermes-home/scripts/<script>.py`
3. Shared OneDrive: `D:/OneDrive/Taadaa_Sync_Shared/hermes-cron/scripts/<script>.py`
