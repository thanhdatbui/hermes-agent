# Account-Scoped Idempotency Receipts & Watchdog Multi-Stage Reporting

## 1. Idempotency Receipt Account Scoping (Tiktok-video)

### Problem & Root Cause
Trên farm Android, 1 thiết bị vật lý chạy luân phiên nhiều tài khoản qua các ca/row khác nhau (Ca 1 / Ca 2 / Ca 3; Row 1, Row 2, Row 4):
- File receipt chống đăng trùng ban đầu chỉ đặt tên theo máy: `machine_{machine}_video_{video_number}.json`.
- Khi tài khoản mới (ví dụ `@thanhlee372` - Row 4) chạy Video 1 trên Máy 37, runner tìm thấy file `machine_37_video_1.json` tồn tại từ trước đó của nick cũ (`@phungloan0138` - Row 1).
- Runner kiểm tra thấy `receipt is not None and not retry_available`, kết luận Video 1 đã được đăng trên máy 37, **từ chối bấm nút Đăng**, nhảy cóc sang `VERIFY_POST` và kết thúc thất bại với `exit_code: 1`.

### Giải pháp Kiến trúc & Fail-Closed Isolation
1. **Account-Scoped Naming**:
   - File receipt mới: `machine_{safe_machine}_account_{safe_account}_video_{video_number}.json`.
2. **Account Scope Isolation Policy (`_is_file_in_scope_for_account`)**:
   - Khi có `target_account`:
     + File có tag account khác (`machine_{m}_account_{other}_video_{v}.json`): **Hoàn toàn OUT-OF-SCOPE**, không đọc payload để tránh cross-contamination.
     + File đúng tag target account: **IN-SCOPE** (exact). Bất kỳ lỗi parse/schema/machine mismatch nào đều phải `fail-closed` (`{"status": "unreadable"}` hoặc pending `(0, path)`).
     + File legacy (`machine_{m}_video_{v}.json`): **IN-SCOPE** (non-exact). Nếu payload chứa `target_account` khác thì bỏ qua; nếu khớp hoặc không có tag thì xét tiếp.
   - Khi `target_account` rỗng (truy vấn machine-level): Tất cả các file thuộc máy đều **IN-SCOPE**. Bất kỳ file nào lỗi/corrupt đều fail-closed.
3. **Direct Canonical Read**:
   - Trong `_load_post_attempt_receipt`, đọc trực tiếp file `expected_account_path`. Chỉ `FileNotFoundError` mới được coi là chưa đăng; mọi lỗi I/O, decode JSON, non-dict, schema thiếu trường, hoặc machine/video mismatch đều fail-closed trả về `{"status": "unreadable"}`.
4. **Schema Validation Chặt chẽ (`_is_valid_receipt_schema`)**:
   - `status`: chuỗi không rỗng.
   - `machine`: `int > 0` hoặc chuỗi không rỗng (loại trừ `bool` và containers).
   - `video_number`: `int > 0` (loại trừ `bool`).

---

## 2. Watchdog Multi-Stage Reporting & Process Lock (tiktok-luot nuoi acc + Hermes)

### Nguyên tắc Báo cáo Tách bạch Cả 2 Script
Không bao giờ gộp chung 1 trạng thái cho cả flow đa công đoạn (Lướt Feed -> Follow chéo -> Đăng Video).
- Phiên 3 (có upload video): Báo cáo watchdog bắt buộc phân tách rõ 3 mục:
  1. **Lướt Feed**: `Success (N): ...` / `Fail (M): ...`
  2. **Follow chéo**: `Success (N): ...` / `Nhả follow (R): ...` / `Lỗi script (E): ...` / `Bỏ qua (K): ...`
  3. **Đăng Video (Phiên 3)**: `Success (N): ...` / `Fail (M): M_x(lý_do)` / `Bỏ qua (K): ...`
- Parser `parse_upload_results`: Đọc trực tiếp `upload_result.json` của từng máy, chuẩn hóa an toàn `exit_code` (int) và `status` (lower-case).
- Parser `parse_follow_results`: Chuẩn hóa an toàn trường `followed` (nếu `None`/non-list thì gán `[]`), tránh crash `len(flist)`.

### Khóa liên tiến trình Kernel-Level (`ProcessLock`)
- Sử dụng `msvcrt.locking` trên Windows và `fcntl.flock` trên POSIX trên file descriptor `a+b`.
- Không dựa vào PID timeout/eviction thủ công (dễ sinh race condition khi 2 tiến trình cùng đọc lock cũ).
- Re-entrant acquire trên cùng 1 instance trả về `False`.
- Tạo thư mục cha an toàn: kiểm tra `os.path.dirname(lock_path)` trước khi gọi `os.makedirs`.

### Xử lý Rollover Qua đêm & Multi-Day Backlog
- Watchdog quét toàn bộ thư mục ngày trong cửa sổ lưu trữ 7 ngày: `retention_cutoff <= date_str <= today_str`.
- Tránh bỏ sót các phiên hoàn thành trễ sau 00:00 hoặc các phiên backlog khi runner chạy liên tục xuyên đêm.
- Khung giờ cuối ngày (Phiên 3 Ca 3 `22:00 - 23:59`):
  + Trong ngày hôm nay: Chỉ report sớm khi **100% số máy dự kiến đã hoàn thành**. Nếu chưa đủ máy, giữ trạng thái hoãn (không report non ở phút 23:59:00).
  + Sang ngày hôm sau (rollover): Khi runner dừng hẳn (`not runner_busy`), chốt báo cáo toàn bộ kết quả ngày hôm trước.

### Cảnh báo Tức thì trên Runner (`multi_machine_feed_session.py`)
- Khi hook upload trả về `status == "failed"`, trả về kiểu bất thường (non-dict), hoặc ném runtime exception:
  Lập tức in log alert ra stdout:
  `[ALERT] [MÁY X] Upload Hook: failed/abnormal_return/exception | Lý do: ...`
  Không để lỗi upload trôi âm thầm trong background.
