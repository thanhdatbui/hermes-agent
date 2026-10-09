# Feed Session Watchdog Rules & Logic

## 1. Quy tắc hàm `can_report_session`
Hàm `can_report_session` trong `feed_session_watchdog.py` quyết định thời điểm watchdog gửi báo cáo tổng kết phiên Telegram:

- **Ưu tiên số 1 - Hoàn tất 100% thật (`completed_expected_count >= expected_count and not has_unattempted_locked`)**:
  - Chốt báo cáo ngay lập tức (`return True`), **kể cả khi `runner_busy=True`**.
  - **Pitfall**: Tuyệt đối KHÔNG đặt `if is_today and runner_busy: return False` ở đầu hàm trước kiểm tra này, vì runner_busy có thể bắt các tiến trình nền uploader/runner khác và sẽ làm fail test / chặn chốt phiên khi toàn bộ máy đã chạy xong thật.

- **Khi chưa hoàn tất hoặc còn lock dở dang (`has_unattempted_locked=True`)**:
  - Đang trong giờ phiên (`now_hm < window_end_hm`): nếu `runner_busy` -> `return False`. Nếu toàn bộ fail (`completed_expected_count == 0`) và run mới nhất >= 15 phút -> `return True`.
  - Đã qua giờ phiên (`now_hm >= window_end_hm`): nếu `runner_busy` -> `return False` (chờ batch kết thúc hẳn).
  - Khi `runner_busy=False`: BẮT BUỘC chốt báo cáo (`return True`).
  - Đối với hôm qua (`is_today=False`): chỉ chốt sau 02:00 sáng hôm nay nếu chưa hoàn tất để tránh chốt vội phiên đêm.

## 2. Đồng bộ các file path song song
Mọi thay đổi trên watchdog script BẮT BUỘC phải kiểm tra và đồng bộ giữa các path liên quan:
1. `D:\Taadaa\tiktok-luot nuoi acc\scripts\feed_session_watchdog.py`
2. `D:\Taadaa\tiktok-luot nuoi acc\scripts\hermes_cron\feed_session_watchdog.py` (nếu có bản mirror cron)
3. `C:\Users\Kibe\AppData\Local\hermes\scripts\feed_session_watchdog.py` (nếu có)

## 3. Tiêu chuẩn vượt ngưỡng Closeout Gate (> 85đ)
- **Observability & No Swallowed Exceptions:**
  - Tuyệt đối CẤM dùng `except Exception: pass` im lặng tại các khối parse JSON/file (`get_all_fleet_machines`, `run_manifest.json`, `summary.txt`).
  - Bắt cụ thể `(json.JSONDecodeError, OSError)` kèm fallback log warning (`logger.warning(...)`) để đảm bảo telemetry minh bạch khi xảy ra lỗi I/O hoặc định dạng dữ liệu.
- **Focused Test Coverage:**
  - Khi sửa bất kỳ logic fallback hoặc parser nào trong watchdog, BẮT BUỘC bổ sung unit test focused trong `python_runner/tests/test_feed_session_watchdog.py` (ví dụ: test config reading fallback, test parse `run_manifest.json` cho `skipped-empty`).
- **Anti-Disk-Scan Invariant:**
  - CẤM dùng `find`, `dir /s`, `grep -rn` quét toàn bộ thư mục gốc repo `tiktok-luot nuoi acc` (do chứa `.git`, `.ai-runs`, `runs`, `runtime` hàng trăm nghìn file gây timeout 180s+). Mở và sửa trực tiếp theo đường dẫn tuyệt đối đã biết.

## 4. Test verification
Chạy test định kỳ bằng:
`pytest "D:/Taadaa/tiktok-luot nuoi acc/python_runner/tests/test_feed_session_watchdog.py" -v`
Đảm bảo tất cả focused tests đều PASS.
