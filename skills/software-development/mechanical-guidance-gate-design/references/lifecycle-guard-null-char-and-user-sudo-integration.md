# Lifecycle Guard Null-Char Exception & User Sudo Override Integration

## 1. Bug: `ValueError: open: embedded null character in path` trong `lifecycle_guard.py`

### Hiện Tượng & Nguyên Nhân
Khi Coordinator chạy các lệnh terminal phức tạp, đặc biệt là `python -c "..."` nhiều dòng chứa xuống dòng, ký tự đặc biệt hoặc quote lồng nhau:
1. `_iter_command_segments()` và `_iter_referenced_shell_scripts()` trong `cron/lifecycle_guard.py` tách các token của dòng lệnh.
2. Một số argument được suy luận nhầm thành `script_path` và chuyển tới `_read_referenced_script(path)`.
3. Tại dòng 259–262:
   ```python
   flags = os.O_RDONLY | getattr(os, "O_NONBLOCK", 0)
   try:
       descriptor = os.open(path, flags)
   except OSError:
       return None, False
   ```
   Trên Windows, khi `path` chứa ký tự null byte hoặc newlines không hợp lệ cho đường dẫn file, `os.open(path, flags)` ném `ValueError: open: embedded null character in path`.
4. Do `ValueError` không kế thừa từ `OSError`, ngoại lệ này không được bắt, văng ra ngoài làm sập toàn bộ tool execution của `terminal`.

### Giải Pháp Đã Sửa & Phòng Tránh
1. **Sửa code cơ học trong `lifecycle_guard.py`:**
   Bắt cả `ValueError`:
   ```python
   except (OSError, ValueError):
       return None, False
   ```
2. **Kỷ luật thi công của Coordinator:**
   - **CẤM** viết các khối mã Python nhiều dòng lồng trong `python -c "..."` qua terminal.
   - **BẮT BUỘC** ghi mã vào file script tạm thời (ví dụ: `D:/Taadaa/tools/tmp_*.py`) bằng `write_file`, sau đó thực thi qua `python D:/Taadaa/tools/tmp_*.py`. Cách này hoàn toàn miễn nhiễm với lỗi phân tích cú pháp của command token parser.

---

## 2. Tích Hợp Cơ Chế User Sudo Override (`user_sudo.py`)

### Mục Tiêu
Giải quyết tình trạng **"Tam Giác Quỷ Bại Liệt Cơ Học"** (Deadlock Triangle):
- Coordinator cạn trần T1 (10 files) không được ghi file.
- Worker subagent bị gán nhãn Read-Only không được cấp Scope Lock.
- Terminal bị cấm các lệnh ghi gián tiếp (`python -c open...`, `>`).
- User đã chỉ đạo trực tiếp (`"tao cho phép"`, `"làm luôn"`, `"force"`, `"bypass"`) nhưng các Hook độc lập không đọc được chat Telegram.

### Kiến Trúc `user_sudo.py`
1. **Single-Use Grant:** Ký số HMAC-SHA256 lưu tại `D:/Taadaa/runtime/sudo_grant.json` kèm TTL 300s.
2. **Target Whitelist & Trần O(1):** Chỉ cho phép tối đa 2 files, $\le 30$ dòng diff, cấm tuyệt đối các file credentials (`.env`, `credentials`, `secret`, `accounts.db`).
3. **Verify & Consume:** Khi Hook pre-tool phát hiện grant hợp lệ, grant sẽ được tiêu thụ (consumed) nguyên tử (atomic file lock), ghi log vào `sudo_audit.jsonl` và cho phép hành động đi qua, triệt tiêu hoàn toàn tình trạng tự trói chân AI.
