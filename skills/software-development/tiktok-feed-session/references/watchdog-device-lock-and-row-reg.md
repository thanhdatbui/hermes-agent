# Feed Session Watchdog & Device Lock Resolution

## 1. Cơ Chế Nhận Diện Đúng Trạng Thái Device-Lock Trong Watchdog (`feed_session_watchdog.py`)
- Khi một tiến trình runner thứ 2 vô tình bị kích hoạt lặp trong lúc tiến trình chính đang chiếm giữ lock của toàn bộ máy farm, tiến trình thứ 2 sẽ thoát sớm với `skipped-device-locked`.
- Trong hàm `parse_run_all`, nếu chỉ dựa vào `summary.txt` ở root mà gán `status: fail, reason: batch-config-error` thì sẽ làm vô hiệu hóa bộ lọc `is_device_locked_skip`.
- Watchdog phải ưu tiên đọc `log.jsonl` tại run root để ghi nhận chính xác `skipped-device-locked` cho từng máy.
- Tuyệt đối không bao giờ chốt báo cáo khi `has_unattempted_locked` còn tồn tại hoặc `runner_busy == True`.

## 2. On-Demand Row Reg Hook (`ensure_row_accounts.py`)
- Khi runner nuôi acc chạy theo từng Row (1..8), hook `_preflight_ensure_accounts` tự động kích hoạt `ensure_row_accounts.py <row>` để kiểm tra các máy bị trống slot.
- Nếu thiếu nick, hệ thống tự động kiểm tra kho mail `gmail_clean_v2.xlsx`, mua mail bù nếu cần, chạy batch reg cho riêng các máy thiếu và đồng bộ ngược lại `taikhoan_run_safe.xlsx`.
