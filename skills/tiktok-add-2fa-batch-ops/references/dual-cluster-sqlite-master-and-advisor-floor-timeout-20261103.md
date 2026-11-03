# Dual-Cluster SQLite Master Architecture & Advisor Floor Timeout Invariant (2026-11-03)

## 1. Sự Cố Timeout Hội Đồng Cố Vấn (User Correction)
- Khi gọi `consult_advisor.py`, Coordinator tự ý gán cờ `timeout: 60` ở lệnh terminal làm ngắt ngang Claude CLI khi đang xử lý kiến trúc.
- **Quy tắc bất biến:** Mọi lệnh terminal tham vấn `consult_advisor.py`, Claude CLI hay planner BẮT BUỘC phải đặt `timeout >= 300` (sàn 300s). CẤM TUYỆT ĐỐI nhồi timeout ngắn (60s/120s) làm rớt ý kiến phản biện của Claude Sonnet và Sol.

## 2. Kiến Trúc Chia Sẻ SQLite farm_master.db Giữa Kibe & Admin
- **Hiện trạng:** `farm_master.db` nằm cục bộ trên Kibe `D:/Taadaa/data/farm_master.db`. Máy Admin chưa có file nên runner 2FA đêm bị fallback về Excel và fail.
- **CẤM đưa vào OneDrive:** Không đặt SQLite WAL trực tiếp trên thư mục sync OneDrive (`D:\OneDrive\TaadaaData\`) vì xung đột file handle `.db-wal` và `.db-shm` gây crash/lock database.
- **Kiến trúc Tác Chiến Độc Lập (Zero Overlap Partitioning):**
  - Kibe quản lý máy 1–80 (640 nick).
  - Admin quản lý máy 201–280 (640 nick).
  - Hai dải máy hoàn toàn không chồng chéo tài khoản.
  - Mỗi máy bắt buộc sở hữu một bản `D:/Taadaa/data/farm_master.db` trên SSD local của mình để Python runner trên máy đó đọc/ghi $O(1) \approx 0.005s$.
  - Đồng bộ/merge số liệu định kỳ giữa 2 máy diễn ra an toàn vì không có xung đột ghi trên cùng tài khoản (Zero Split-Brain).
