# Farm Safety: Strict Prohibition of Wide-Scope Disk / Repo Grep

## 🛑 BẮT BUỘC: TUYỆT ĐỐI CẤM QUÉT ĐĨA DIỆN RỘNG KHI NHẬN ALERT
1. **Lệnh duy nhất khi nhận alert `[MÁY N]`**:
   `python D:/Taadaa/tools/inspect_machine.py <N>`
2. **CẤM TUYỆT ĐỐI**:
   - Dùng `grep -rn` hoặc `grep -r` không giới hạn thư mục trên toàn ổ `D:/Taadaa` hay codebase lớn.
   - Dùng `os.walk`, `glob(recursive=True)`, `find`, `search_files` quét diện rộng để tìm file log / artifact.
3. **Chỉ đọc trực tiếp theo đường dẫn xác định**:
   - File flow: `python_runner/flows/feed_swipe_smoke.py`, `benign_popup_registry.py`, `benign_popup.py`.
   - File test: `python_runner/tests/test_...py`.
   - Trạng thái thiết bị: Gọi ADB trực tiếp theo serial hoặc qua `inspect_machine.py`.
