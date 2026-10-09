# ADB Daemon Hang, Broad-scan Pitfall & CLI Flags Pitfall (2026-09-27)

## 1. ADB Daemon Hang Recovery trên Windows Host
- **Triệu chứng**: `inspect_machine.py <N>` hoặc bất kỳ lệnh ADB nào bị timeout 10.0s liên tục (`Command '['...adb.exe', 'shell', ...]' timed out after 10.0 seconds`).
- **Nguyên nhân**: Tiến trình `adb.exe` daemon chạy ngầm bị deadlock/treo kết nối USB socket với thiết bị.
- **Biện pháp xử lý dứt điểm O(1)**:
  ```bash
  taskkill -F -IM adb.exe
  "C:/Program Files (x86)/xiaowei/tools/adb.exe" start-server
  python D:/Taadaa/tools/inspect_machine.py <N>
  ```
  Sau khi kill và restart, kiểm tra lại trạng thái máy ngay để xác nhận thiết bị đã online bình thường.

## 2. Cấm Tuyệt Đối Recursive Grep Trên Cây Thư Mục Test/Temp
- **Triệu chứng**: Chạy `grep -rn "keyword" /d/Taadaa/Tiktok_Reg/` bị `grep: .pytest-basetemp-...: Permission denied` và kẹt terminal timeout 600s.
- **Nguyên nhân**: Các thư mục cache test (`.pytest-basetemp-*`, `.ai-runs`, `.pytest_cache`) trên Windows có phân quyền chặt và chứa hàng ngàn file rác/socket/lock.
- **Quy tắc bất biến**:
  - TUYỆT ĐỐI CẤM quét diện rộng qua toàn bộ repo.
  - Khi cần đọc log hoặc UI XML, CHỈ trích xuất đích danh file theo timestamp/prefix cụ thể trong `D:/Taadaa/runtime/kibe/artifacts/ui_dumps/` hoặc thư mục run của batch.

## 3. Cờ CLI và Biến Môi Trường trong `tiktok_login_v1.py`
- **Pitfall**: `tiktok_login_v1.py` có parser argparse riêng và KHÔNG nhận các cờ `--no-feed-after-reg`, `--no-avatar-after-reg`. Truyền các cờ này vào command-line sẽ gây lỗi:
  `tiktok_login_v1.py: error: unrecognized arguments: --no-feed-after-reg --no-avatar-after-reg` (exit code 2).
- **Cách cấu hình đúng**:
  Để tắt feed warmup và avatar hook sau khi login, truyền qua biến môi trường trước khi chạy script:
  ```bash
  export TIKTOK_REG_FEED_AFTER_REG=0
  export TIKTOK_REG_AVATAR_AFTER_REG=0
  python D:/Taadaa/Tiktok_Reg/tiktok_login_v1.py <STT> --email <TARGET> --ss
  ```
