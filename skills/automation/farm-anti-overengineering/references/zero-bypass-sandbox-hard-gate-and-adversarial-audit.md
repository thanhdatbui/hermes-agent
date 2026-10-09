# Zero-Bypass Sandbox Hard Gate & Claude Opus Adversarial Audit

Tài liệu này ghi lại kiến trúc chuẩn và các bài học rút ra từ quá trình triển khai Hard Gate cấp 4 (`farm-coordinator-guard` v4.4) và cuộc đối kháng thẩm định đa vòng với Claude Code CLI (Opus High).

---

## 1. Bối cảnh & Vấn đề cốt lõi
- **Triệu chứng:** Coordinator giao task cho Worker subagent nhưng không kèm đường dẫn file cụ thể hoặc chỉ nói chung chung ("tìm hàm...", "trong repo..."). Hậu quả là Worker mất 10-15 tool calls lượn khắp các ổ đĩa để tìm file, gây cạn budget hoặc timeout.
- **Giải pháp ban đầu:** Nạp quy tắc Scope Lock vào Memory và System Prompt.
- **Lỗ hổng của Soft Constraints:** Claude Opus High chỉ rõ: Memory / System Prompt là Soft Constraints mang tính xác suất. Khi context phình to hoặc khi gặp Alert khẩn cấp, mô hình sẽ bị "Lost in the middle" và bypass memory.
- **Giải pháp triệt để:** Bắt buộc dùng **Python Pre-tool Hook Plugin (Hard Gate cấp 4)** chặn đứng `delegate_task` trước khi nó được phát đi nếu không thỏa mãn Scope Lock.

---

## 2. Bốn nguyên lý kiến trúc Zero-Bypass (Claude Opus High Certified)

### Nguyên lý 1: Fail-Closed Identity Resolution (Mặc định Deny)
- **Lỗ hổng:** Nếu một session mới không tìm thấy `parent_session_id` trong database hoặc state file, code cũ mặc định coi đó là Coordinator (`return None` cho qua).
- **Khắc phục:** Mọi session không chứng minh được danh tính Coordinator (không có `is_coordinator: True` hoặc parent không rõ ràng) BẮT BUỘC bị coi là **Worker** (nguyên lý Least Privilege) và bị áp toàn bộ quy tắc sandbox nghiêm ngặt nhất.

### Nguyên lý 2: Value-Scanned Parameter Agnosticism (Cấm đoán tên tham số)
- **Lỗ hổng:** Gate kiểm tra file ghi chỉ đọc `fn_args.get("path")`. Kẻ tấn công hoặc model có thể truyền file đích vào các key khác như `file_path`, `target`, `filename`, `content`, hoặc nhúng file đích bên trong nội dung diff/patch (`*** Update File: C:/Windows/...`).
- **Khắc phục:**
  - Viết hàm `_extract_all_string_values(fn_args)` quét đệ quy mọi chuỗi trong dict/list tham số để kiểm tra blacklist hệ thống (`hermes`, `state.db`, `farm-coordinator-guard`, `.ssh`).
  - Viết hàm `_extract_all_patch_targets(fn_args)` quét toàn bộ nội dung text để trích xuất đầy đủ các file directive của định dạng patch V4A (`*** Update File:`, `*** Add File:`, `*** Delete File:`, `*** Move to:`, `+++ / ---`).
  - Nếu `mode='patch'` mà không trích xuất được file header hợp lệ nào ➔ **FAIL-CLOSED BLOCK `UNPARSEABLE PATCH`**.

### Nguyên lý 3: Hermetic Shell & Strict Command Whitelist
- **Lỗ hổng:** Cho phép worker chạy `git` hoặc `python` với cờ mở rộng. Worker có thể lợi dụng `git -c core.pager=...` hoặc `python -c "..."` để thực thi mã tùy ý (RCE escape).
- **Khắc phục:**
  - Chặn đứng 100% ký tự điều khiển shell và nối lệnh: `; & | \` $ > < ( ) % ^ \r \n`.
  - Phân tích cú pháp qua `shlex.split(cmd, posix=False)`.
  - Giới hạn lệnh `git` chỉ cho phép 3 subcommand đọc: `status`, `diff`, `log` và CẤM TOÀN BỘ cờ lạ (`tok.startswith("-")`).
  - Mọi token tham số (kể cả tên file trần sau cờ `--`) đều bị giải phân qua `os.path.realpath` và bắt buộc nằm trong `ALLOWED_REPO_ROOTS` (`D:\Taadaa`).

### Nguyên lý 4: Symmetric Defense-in-Depth (Bảo vệ đối xứng)
- Cả Worker lẫn Coordinator đều bị ràng buộc không được ghi file ngoài danh sách cho phép:
  + Worker: Bị giới hạn duy nhất trong `D:\Taadaa` VÀ đúng `Scope Lock` được Coordinator cấp phép.
  + Coordinator: Bị giới hạn trong `D:\Taadaa` và `HERMES_ROOT`.
- Mọi thao tác ghi đụng vào file nguồn của plugin bảo vệ hoặc `state.db` đều bị chặn vô điều kiện cho mọi actor.

---

## 3. Quy trình Thẩm định & Giới hạn Claude Code CLI
- Khi gọi `claude -p --model opus --effort high` để thẩm định mã nguồn:
  - Cần bọc diff trong file markdown tạm, không nhúng trực tiếp vào bash command để tránh bash escaping lỗi cú pháp.
  - Chú ý giới hạn phiên 5 giờ của Anthropic Claude Pro: Nếu gửi prompt dài liên tục trên 10-15 lần, tài khoản sẽ chạm hạn mức (`You've hit your session limit`).
  - Khi đã có phán quyết `APPROVED` từ Claude Opus, các caveat phụ nên được giải quyết nhanh gọn và kiểm chứng bằng test suite `pytest` độc lập thay vì spam lệnh review làm cạn kiệt quota.
