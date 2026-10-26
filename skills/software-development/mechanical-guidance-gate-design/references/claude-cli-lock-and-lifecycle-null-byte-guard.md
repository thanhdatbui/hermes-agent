# Claude CLI Pre-Tool Lock & Lifecycle Guard Null-Byte Invariant

## 1. Ổ Khóa Cơ Học Chặn Lạm Dụng Claude CLI (`guard_claude_cli_lock.py`)

### Bối Cảnh & Triệu Chứng Lạm Dụng
- **Hiện tượng:** Khi gặp khó khăn trong việc soi ảnh, crop avatar, nhận diện tọa độ UI hoặc sợ sai, Coordinator có xu hướng lười biếng và ỷ lại vào Claude CLI (`claude -p`), liên tục gọi Claude để soi từng pixel, đọc nút bấm, đo tọa độ thay vì dùng các công cụ cục bộ (`OpenCV`, `WinRT OCR`, `Python stdlib`).
- **Hậu quả:** Đốt cạn quota 5 giờ và quota tuần của User, làm che giấu các bug thực sự trong runner tự động (`state_machine.py`), vi phạm nghiêm trọng tính tự chủ và kỷ luật của hệ thống.

### Cơ Chế Khóa Cơ Học (PreToolUse Hook)
- **Tập tin hook:** `D:/Taadaa/tools/guard_claude_cli_lock.py` được đăng ký vào `hooks.pre_tool_call` của Hermes (`matcher: terminal`, `timeout: 5`).
- **Quy tắc chặn (Fail-Closed):** Mọi câu lệnh gọi trực tiếp `claude`, `claude -p`, `claude.exe`, hoặc qua script wrapper (`claude_worker.py`) đều bị chặn đứng ngay lập tức, TRỪ CÁC NGOẠI LỆ ĐÃ XÁC THỰC:
  1. **Lệnh chỉ đọc an toàn:** `claude --version`, `-v`, `--help`, `-h`, `doctor`, `auth status`.
  2. **Cờ môi trường:** `CLAUDE_USER_APPROVED=1` hoặc `ALLOW_CLAUDE_OVERRIDE=1`.
  3. **User Sudo Grant:** Tồn tại file `D:/Taadaa/runtime/sudo_grant.json` còn hạn, chưa sử dụng (`used: false`), và cấp quyền cho `claude`.
  4. **Reviewer Hand-off Token:** Tồn tại file `D:/Taadaa/runtime/reviewer_handoff.token` với trạng thái `STRIKE_3_HANDOFF_ACTIVE` còn trong hạn TTL.
- **Xử lý khi vi phạm:** Ghi nhật ký vào `D:/Taadaa/runtime/audit_logs/claude_lock_audit.jsonl`, phát thông điệp chặn `CLAUDE_CLI_LOCKED` và kết thúc với `sys.exit(0)`.

---

## 2. Lỗi Null Character ValueError trong `lifecycle_guard.py`

### Triệu Chứng
Khi Coordinator thực thi câu lệnh terminal chứa chuỗi Python nhiều dòng hoặc tham số phức tạp trên Windows, lệnh bị ngắt đột ngột với thông báo:
```text
ValueError: open: embedded null character in path
```

### Căn Nguyên
Trong `cron/lifecycle_guard.py` (hàm `_read_referenced_script`):
```python
# Code cũ:
try:
    descriptor = os.open(path, flags)
except OSError:
    return None, False
```
`os.open()` trên Windows ném `ValueError` khi gặp đường dẫn chứa ký tự NUL. Vì `ValueError` không kế thừa từ `OSError`, exception không được bắt và văng ra ngoài, làm sập toàn bộ bộ lọc terminal của Coordinator.

### Giải Pháp Đã Vá
Bắt cả hai loại ngoại lệ một cách an toàn:
```python
try:
    descriptor = os.open(path, flags)
except (OSError, ValueError):
    return None, False
```
Đã được kiểm chứng tự động qua unit test `tests/test_lifecycle_guard_patch.py` (3/3 test pass 100%).
