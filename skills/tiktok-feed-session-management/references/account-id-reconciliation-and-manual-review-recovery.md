# Account-ID Reconciliation & Follow Manual Review Recovery Invariants

## 1. Nguyên Tắc Đối Soát Web Theo Account ID (Thay vì Row Máy)
- **Bản chất dữ liệu:** Bảng SQLite `snapshots` trong `D:/Taadaa/data/tiktok_tracker.db` chỉ lưu khóa `(username, following, timestamp)`, hoàn toàn không có cột `row` hay `machine`.
- **Rủi ro của Row Máy:** Khi đối soát theo `row máy`, ở các ca hỗn hợp (`active_row = -1`) hoặc ca chạy slot linh hoạt, watchdog dễ lấy nhầm nick slot khác (ví dụ Máy 40 chạy Row 2 `@nguyenkhoi1403` nhưng watchdog lại lấy Row 1 `@charakrh768` $\to$ gây ra lệch âm ảo -3 follow và báo oan nick bị nhả).
- **Quy chuẩn kiến trúc đối soát:**
  1. `multi_machine_feed_session.py`: Mọi hook ghi nhận kết quả (`_write_follow_result`, `_write_upload_result`) BẮT BUỘC inject trường `"account"` (`expected_username` thực tế đang chạy trên máy).
  2. `parser.py` & `merger.py`: Luôn trích xuất và bảo toàn trường `"account"` từ `follow_result.json`, `upload_result.json` và fallback cào từ `summary.txt` (`"username": "@..."`).
  3. `feed_session_watchdog.py`: Hàm `reconcile_cluster_following` ưu tiên tuyệt đối lấy `account` để truy vấn trực tiếp DB:
     `SELECT following, timestamp FROM snapshots WHERE LOWER(username) = LOWER(?) ...`
  4. **Tự động gắn nhãn Tik:** Sau khi xác định ID acc, watchdog tra cứu vị trí slot trong `machine_slots` để hiển thị nhãn chuẩn: `M{m} [Tik {tik_idx}] (@{username})`.
  5. **Upload Ledger:** `is_machine_upload_successful_in_shift` hỗ trợ tra cứu kép theo cả `(machine, row, date)` và `(machine, account, date)` trong `shift_upload_history.json`.

## 2. Xử Lý Lỗi Follow "MANUAL_REVIEW" & Chống Rơi Rụng Follow Đã Thực Thi
- **Bẫy Bio Mention trong Path B (`mode2_follow_followers.py`):**
  - Khi nút follow trên hàng follower đã chuyển sang "Đang follow", bước kiểm chứng Path B mở profile nick đó để đối soát.
  - `profile_identity_from_xml` tìm chuỗi `@` đầu tiên trên màn hình. Nếu nick có bio ghi tài khoản khác (ví dụ: `IG: @xyz`, `Backup: @abc`), hàm này lấy nhầm `@` trong bio làm username gây ra `identity_mismatch`.
  - **Quy tắc:** Cho phép `handle_is_valid` từ `_find_header_handle_node` (được neo cứng ở dải header `y < 650`) làm nguồn chứng minh danh tính độc lập:
    `if handle_is_valid or identity_is_valid: dump_ok = True`
- **Bẫy Suggested Accounts Sheet sau Tap (`verify_follow.py`):**
  - Ngay sau khi bấm Follow trong Mode 1, TikTok thường bật lên khay gợi ý tài khoản ("Tài khoản tương tự") chứa nhiều handle `@...` khác che khuất một phần header $\to$ gây ra `identity_mismatch`.
  - **Quy tắc:** Khi gặp `identity_mismatch` sau tap, BẮT BUỘC gọi `_reload()` (pull down refresh hoặc re-entry) để đóng khay gợi ý và tải lại profile sạch sẽ trước khi kết luận `MANUAL_REVIEW`.
- **Bảo Toàn Follow Khi Timeout (Follow State Salvage):**
  - Khi tiến trình con của follow hook bị timeout (`follow-timeout` / `follow-hard-deadline-timeout`), CẤM TUYỆT ĐỐI gán cứng `followed_count = 0`.
  - BẮT BUỘC đọc file state `D:/Taadaa/tiktok-follow/runs/state/follow_state_{machine}_row_{row}.json` để vớt (salvage) toàn bộ danh sách nick đã follow thành công trong ngày, bảo toàn số liệu thực tế đã tap ăn lên server.
