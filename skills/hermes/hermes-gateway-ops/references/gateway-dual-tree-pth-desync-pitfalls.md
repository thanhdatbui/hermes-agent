# Gateway Runtime Dual-Tree Pitfalls (hermes_dev.pth & Watchdog Spawn)

## Ngữ cảnh & Triệu chứng Sự cố (2026-11-02)
- Khi tồn tại 2 bản code: bản git repo đang dev (`D:\Taadaa\Hermes`) và bản runtime venv (`C:\Users\Kibe\AppData\Local\hermes\hermes-agent`).
- File `hermes_dev.pth` chèn `D:\Taadaa\Hermes` lên đầu `sys.path`.
- **Triệu chứng crash loop:** Khi Gateway bị restart (bởi lệnh hoặc watchdog), tiến trình Gateway khởi động lại và import module (ví dụ `cron`). Nếu bản ở `D:` bị khuyết hàm hoặc module mà bản `C:` có (như `atomic_write_text`, `read_user_config_raw`, `cron_model_drift_guard_enabled`), Gateway sẽ crash ngay lập tức với `ImportError`.
- **Hậu quả:** Gateway vừa kết nối Telegram thì sập ngay. Watchdog thấy process biến mất lại spawn lại mỗi 2 phút, tạo thành crash loop liên hoàn, khiến kênh Telegram và AI proxy (Omni) bị đứt kết nối kéo dài.

## Quy tắc Kiểm tra & An Toàn Bắt Buộc Trước Khi Restart Gateway
1. **CẤM restart mù khi chưa kiểm tra tính tương thích giữa D: và C:**
   - Tuyệt đối không gọi restart khi chưa xác nhận bản `D:` có đầy đủ module mà runtime đòi hỏi.
   - Kiểm tra import offline trước:
     ```bash
     python -c "import sys; sys.path.insert(0, 'D:/Taadaa/Hermes'); import utils, cron; from hermes_cli import config; print('OK')"
     ```
2. **Cấu hình Watchdog chuẩn khi dùng Dev Tree:**
   - Script watchdog (`hermes-gateway-watchdog.ps1`) khi spawn gateway phải trỏ đúng Python venv và đặt WorkingDirectory cố định về thư mục repo chính (`D:\Taadaa\Hermes`).
3. **Chiến lược Dual-Tree an toàn (Không xóa vội bản C):**
   - Không được hấp tấp xóa bản venv C: hoặc tháo `hermes_dev.pth` khi chưa đối soát và hợp nhất hoàn chỉnh các commit upstream vào repo D:. Bản C đóng vai trò fallback cho các dependencies phụ trợ.
   - Khi có desync, ưu tiên bù đủ các hàm tiện ích (`utils.py`, `config.py`) sang D: để D: tự thân import thành công trước.
