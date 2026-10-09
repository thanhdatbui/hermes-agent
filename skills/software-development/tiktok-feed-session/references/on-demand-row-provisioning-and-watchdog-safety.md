# Quy tắc On-Demand Provisioning & Watchdog Lock Safety (2026-09-14)

## 1. Cơ chế On-Demand Reg bù theo Row (ensure_row_accounts.py)
- **Mục đích:** Đảm bảo khi đến giờ chạy bất kỳ Row nào (Row 1..8), nếu máy nào thiếu nick thì tự động reg bù ngay tại máy đó trước khi chạy Feed lướt nuôi acc.
- **Script điều phối trung tâm:** `D:/Taadaa/tools/ensure_row_accounts.py <row>`
- **Hook tích hợp runner:** `_preflight_ensure_accounts(row, window_key)` trong `C:/Users/Kibe/AppData/Local/hermes/scripts/tiktok_runner.py`.
- **4 bước tự động hóa:**
  1. Quét `taikhoan_run_safe.xlsx` tìm các máy có slot ở Row đó trống (`ID == None`).
  2. Đối chiếu kho `gmail_clean_v2.xlsx` xem máy đó đã có sẵn mail sạch chưa. Nếu thiếu -> gọi `buy_hotmail.py` mua Hotmail OAuth2 nạp vào.
  3. Kích hoạt `_run_all_targets.py` reg TikTok riêng cho danh sách máy thiếu này.
  4. Merge kết quả vào tracking và đồng bộ sang `taikhoan_run_safe.xlsx`.
- **Lệnh kiểm tra O(1) không ghi đĩa:**
  ```bash
  python D:/Taadaa/tools/ensure_row_accounts.py <row> --dry-run
  ```

## 2. Phòng tránh False Alert từ Watchdog do Race Condition Device-Lock
- **Hiện tượng:** Khi 2 runner trigger trùng nhau trong cùng một window (cách nhau 1-2 phút), runner thứ hai gặp lock toàn bộ máy -> sinh ra thư mục artifact với `skipped-device-locked: 78` và kết thúc sau vài giây.
- **Nguyên nhân bug Watchdog:** Nếu watchdog duyệt `summary.txt` ở root của batch run và mù quáng gán status `fail / batch-config-error`, hàm kiểm tra máy hoàn tất (`real_completed`) sẽ ngộ nhận toàn bộ máy đã chạy xong và chốt báo cáo ảo đè lên runner chính đang chạy thật.
- **Quy tắc xử lý trong watchdog (`feed_session_watchdog.py`):**
  1. BẮT BUỘC đọc `log.jsonl` tại run root để trích xuất chính xác trạng thái từng máy (`skipped-device-locked`).
  2. Tuyệt đối KHÔNG gán mặc định `fail` cho máy bị lock.
  3. Khi phát hiện một batch run mà toàn bộ máy bị `skipped-device-locked`, watchdog phải bỏ qua và chờ runner chính đang active hoàn tất.
