# Watchdog Feed Session: Đồng bộ & Quy tắc Merge Số liệu

## 1. Đồng bộ Watchdog song song giữa Hermes và Repo
Script watchdog phân tích phiên feed (`feed_session_watchdog.py`) cùng file test tồn tại song song ở hai vị trí:
- `C:\Users\Kibe\AppData\Local\hermes\scripts\feed_session_watchdog.py` (và `test_feed_session_watchdog.py`)
- `D:\Taadaa\tiktok-luot nuoi acc\scripts\feed_session_watchdog.py`

Khi chỉnh sửa extraction hoặc logic merge kết quả:
- **BẮT BUỘC cập nhật đồng thời ở CẢ HAI file** để runner của repo và cron/watchdog service của Hermes đồng bộ dữ liệu thống kê.

## 2. Quy tắc trích xuất & merge `feed_counts`
- Khi trích xuất `summary.txt` từng máy:
  - Bổ sung tìm khối `"feed_counts":` tương tự như `"like_counts":`.
  - Quét số lượng vuốt theo các tab: `for-you`, `following`, `friends`.
  - Đóng gói vào payload: `feed_counts: feed_counts_map`.
- Trong `merge_machine_result`:
  - Phải merge `feed_counts` tích lũy across runs tương tự như `likes` (lấy `max` số lượng theo từng tab giữa `prev` và `new`).
- Trong báo cáo thống kê:
  - Sử dụng `feed_counts` để tính tỷ lệ like từng tab (`tot_fy_likes / tot_fy_swipes * 100.0`, tương tự cho `following` và `friends`).

## 3. Quy trình verify bắt buộc
1. Chạy `python -m py_compile` trên cả hai file watchdog script.
2. Chạy `pytest` trên `test_feed_session_watchdog.py` để verify các hàm merge và tính toán tỷ lệ trước khi chốt.
