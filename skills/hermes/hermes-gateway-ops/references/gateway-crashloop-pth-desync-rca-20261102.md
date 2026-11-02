# Incident RCA & Recovery: Gateway Crash Loop via hermes_dev.pth Sys.path Desync

## 1. Bản chất sự cố (Root Cause)
- File `hermes_dev.pth` chèn `D:\Taadaa\Hermes` lên đầu `sys.path`.
- Bình thường khi Gateway chạy nền từ process cũ hoặc trên venv `C:`, code vẫn ổn định.
- Khi Agent tùy tiện ra lệnh restart Gateway (đặc biệt khi chưa audit môi trường):
  * Process mới khởi động buộc phải nạp code từ `D:\Taadaa\Hermes`.
  * Repo `D:\` bị khuyết nhiều module và hàm trọng yếu so với venv `C:` (ví dụ: `atomic_write_text` trong `utils.py`, `read_user_config_raw`, `cron_model_drift_guard_enabled` trong `hermes_cli/config.py`, và 123 file untracked khác).
  * Gateway vừa import `cron` và kết nối Telegram là văng `ImportError` ngay lập tức, tiến trình chết tức thì.
  * Watchdog service quét định kỳ (mỗi 2 phút) thấy Gateway chết liền tự động spawn lại -> gây ra vòng lặp crash loop liên tục suốt 30+ phút, làm tê liệt toàn bộ kết nối Omni/Telegram.

## 2. Các điểm vá nóng bắt buộc (Hotfix Artifacts)
1. **`utils.py` (Repo D):** Phải có hàm `atomic_write_text(path, text, *, tmp_prefix=None, mode=None)` dùng `mkstemp` + `atomic_replace` đảm bảo fsync chống torn file.
2. **`hermes_cli/config.py` (Repo D):** Phải có `read_user_config_raw(config_path=None)` và `cron_model_drift_guard_enabled(config=None)`.
3. **Bổ sung 123 file thiếu từ venv sang Repo D:** Đảm bảo toàn bộ các module con trong `gateway/`, `agent/`, `hermes_cli/`, `tools/` đều có mặt đầy đủ ở repo `D:`.
4. **Watchdog (`hermes-gateway-watchdog.ps1`):** Phải set `GatewayWorkDir = 'D:\Taadaa\Hermes'` và spawn Python venv trực tiếp với thư mục làm việc chuẩn.

## 3. Quy tắc Invariant chống tái diễn
- **CẤM TUYỆT ĐỐI restart Gateway khi chưa verify sys.path & import:**
  Trước khi restart, bắt buộc chạy dry-run import kiểm tra tính toàn vẹn:
  ```bash
  python -c "import sys; sys.path.insert(0, 'D:/Taadaa/Hermes'); import utils; import cron; from hermes_cli import config; print('PRE-RESTART CHECK: OK')"
  ```
- **Hợp nhất Single Source of Truth & Cạm bẫy xóa nhầm Virtualenv ổ C:**
  * **Tại sao CẤM xóa thẳng tay thư mục C:** Thư mục bản C (`hermes-agent`) không chỉ chứa code cũ mà còn là nơi lưu trữ **môi trường ảo Python (`venv`)**, bao gồm trình thông dịch `python.exe` và toàn bộ các package/thư viện bên thứ ba đã compile (`httpx`, `telethon`, `playwright`, `pyyaml`...). Xóa thư mục C đồng nghĩa với việc xóa sạch runtime, Gateway sẽ chết hoàn toàn do mất môi trường thực thi.
  * **Kiến trúc phân tầng chuẩn:**
    1. `D:\Taadaa\Hermes` là **Single Source of Truth duy nhất** cho toàn bộ source code (mọi chỉnh sửa logic, gate, guard, hook đều thực hiện tại đây).
    2. File `hermes_dev.pth` đặt tại `site-packages` của venv để cưỡng chế nạp code từ `D:\Taadaa\Hermes` lên đầu `sys.path`.
    3. Watchdog (`hermes-gateway-watchdog.ps1`) gọi Python từ venv ổ C nhưng đặt thư mục làm việc cố định tại `D:\Taadaa\Hermes`.
    4. Giữ thư mục C thuần túy làm **runtime container** chứa dependency, không duy trì code sửa tay tại C.
