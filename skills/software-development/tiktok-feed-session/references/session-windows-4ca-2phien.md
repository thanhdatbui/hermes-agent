# Kiến Trúc Ca & Phiên Nuôi Feed (4 Ca x 2 Phiên) & Đồng Bộ Watchdog

## 1. Cấu Trúc Khung Giờ Mới (4 Ca x 2 Phiên)

Từ tháng 09/2026, toàn bộ hệ thống nuôi acc TikTok chuyển đổi từ mô hình 3 Ca x 3 Phiên sang **4 Ca x 2 Phiên**:

- **Ca 1 (Sáng)**:
  - Phiên 1: `06:00 - 07:30` (Lướt feed + Follow)
  - Phiên 2: `07:30 - 10:00` (Lướt feed + Follow + Đăng video)
- **Ca 2 (Trưa - Chiều)**:
  - Phiên 1: `12:00 - 13:30` (Lướt feed + Follow)
  - Phiên 2: `13:30 - 16:00` (Lướt feed + Follow + Đăng video)
- **Ca 3 (Tối)**:
  - Phiên 1: `18:00 - 19:30` (Lướt feed + Follow)
  - Phiên 2: `19:30 - 22:00` (Lướt feed + Follow + Đăng video)
- **Ca 4 (Đêm)**:
  - Phiên 1: `00:00 - 01:15` (Lướt feed + Follow)
  - Phiên 2: `01:15 - 03:00` (Lướt feed + Follow + Đăng video)
- **Khung nghỉ đêm / bảo trì / reg acc**: `03:00 - 06:00`.

## 2. Phân Chia Row / Lanes (Chẵn / Lẻ)

- **Ngày Lẻ (Lane B)**:
  - Ca 1: Row 1
  - Ca 2: Row 3
  - Ca 3: Row 5
  - Ca 4: Row 7
- **Ngày Chẵn (Lane A)**:
  - Ca 1: Row 2
  - Ca 2: Row 4
  - Ca 3: Row 6
  - Ca 4: Row 8

## 3. Quy Tắc Upload Hook (Phiên 2)

- Trong mô hình cũ (3 ca x 3 phiên), upload hook kích hoạt ở Phiên 3 (`session_index == 3`).
- Trong mô hình mới (4 ca x 2 phiên), upload hook chuyển sang kích hoạt ở **Phiên 2** (`session_index == 2`).
- Khi sửa đổi runner (`multi_machine_feed_session.py`), `_effective_session_index(config) == 2` quyết định quyền upload.
- Trong watchdog (`feed_session_watchdog.py`), bộ lọc phân loại upload phải kiểm tra `win["phien"] in (2, 3)` hoặc `"Đăng video" in win["name"]` để bao quát đúng Phiên 2 mới và tương thích ngược.

## 4. Bắt Buộc Đồng Bộ 2 Vị Trí `feed_session_watchdog.py`

Watchdog chạy nền báo cáo Telegram có 2 bản cần giữ đồng nhất tuyệt đối:
1. `C:\Users\Kibe\AppData\Local\hermes\scripts\feed_session_watchdog.py` (Script chạy thực tế của Hermes daemon).
2. `D:\Taadaa\tiktok-luot nuoi acc\scripts\hermes_cron\feed_session_watchdog.py` (Source code trong repo git).

**Quy trình chuẩn khi cập nhật:**
1. Sửa file tại một bên hoặc cả hai bên.
2. Kiểm tra `filecmp.cmp` hoặc so sánh diff để đảm bảo không bị lệch code giữa local runtime và repo git.
3. Chạy `python -m py_compile` kiểm tra syntax trên cả 2 đường dẫn.
