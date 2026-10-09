# Preflight Cookie Guard & Closeout Gate Test Suite for GPM Gmail Nurture

## 1. Cơ Chế Preflight Cookie Guard O(1)
- **Vấn đề**: Khi mở profile GPMLogin bằng Playwright CDP chỉ để kiểm tra cookie session Google, mỗi profile tốn 10–15s. Nếu 1 batch gặp nhiều profile mất session Google (`0 token`), việc start/stop browser liên tục làm nghẽn tài nguyên và timeout toàn batch.
- **Giải pháp O(1)**: Đọc trực tiếp file SQLite Cookies Chromium trên đĩa trước khi khởi động profile:
  - Đường dẫn: `<GPM_PROFILE_BASE>/<profile_path>/Default/Network/Cookies`
  - Điều kiện chấp nhận: Bắt buộc tìm thấy $\ge 2$ token xác thực Google (`SID`, `SSID`, `HSID`, `SAPISID`).
  - Corrupt DB Handling: Bọc `sqlite3.connect` bằng `try/except (sqlite3.DatabaseError, OSError)` để trả về `False` an toàn mà không làm crash script.
  - Gắn cờ `NEEDS_LOGIN`: Đánh dấu ngay vào `gpm_gmail_nurture_state.json` và bỏ qua profile đó ở các lần quét nuôi tiếp theo, định tuyến sang watchdog cấp lại phiên.

## 2. Các Invariants Bắt Buộc Để Đạt Closeout Gate (>= 85đ)
Khi thẩm định với Sol Reviewer (`closeout_gate.py`), bộ test phải bao phủ các invariants sau:
1. **Float Group ID Strictness**:
   - Chỉ chấp nhận integer hoặc float nguyên (`10.0`, `"10"`).
   - Từ chối float không nguyên (`10.5`, `10.7`) để tránh làm tròn thành group 10.
2. **Lifecycle & Failover API GPM**:
   - `stop_gpm_profile(profile_id)` phải thử endpoint `close` trước, sau đó fallback sang `stop`.
   - Bắt mọi ngoại lệ network khi API GPM không phản hồi.
3. **Multi-threading & File State Concurrency**:
   - `save_state` phải thực hiện ghi atomic (`.tmp` -> `os.replace`).
   - Telemetry JSONL ghi log với lock đa luồng và cơ chế rotate khi kích thước vượt trần 10MB.
4. **Cách Ly Diff Khi Monorepo Có Nhiều File Uncommitted**:
   - Tránh dùng `--repo <path>` khi repo đang dirty nhiều file khác ngoài phạm vi (dễ vượt trần 32KB của `sol_payload_guard.py` và bị đánh trượt do truncation).
   - Xuất diff tập trung: `git diff -- <script> <test> > scoped.diff` và chạy `closeout_gate.py --input scoped.diff`.
