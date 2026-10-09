# Post-Feed Background Waiter & Chained Batch Execution Pattern

Khi cần kích hoạt một batch job hoặc chuỗi cron phụ thuộc (ví dụ: `post_noon_chain_watchdog.py`, Reg Gmail -> Add 2FA TikTok) ngay sau khi ca nuôi feed kết thúc mà không thể block toàn bộ cron timeout hoặc đợi người dùng gõ lệnh thủ công:

## 1. Bản chất vấn đề
- Feed session thường chạy 80 máy và kéo dài từ 40 - 90 phút.
- Cron turn của Coordinator có thời lượng giới hạn và không nên treo foreground sleep polling hàng giờ (lãng phí context & timeout).
- Chạy vội khi feed session chưa nhả lock sẽ gây xung đột tài nguyên ADB, đụng độ app và crash chéo giữa các runner.

## 2. Mô hình Waiter Chạy Nền (Non-blocking Background Waiter)
- Tạo một kịch bản daemon độc lập nhẹ (như `post_noon_waiter.py`) thực hiện:
  1. Thăm dò định kỳ (mỗi 30s - 60s):
     - Kiểm tra process feed (`multi-machine-feed-session`, `run-feed-session.ps1`, `run_follow`, v.v.).
     - Kiểm tra active device locks tại cả hai thư mục:
       - `C:\Users\Kibe\AppData\Local\automation-core\device-locks`
       - `C:\Users\Kibe\.codex\device-locks`
       (status in `['active', 'running', 'queued', 'blocked']` hoặc còn file `.lock`).
  2. Khi `active_feed_pids == 0` và `active_locks == 0`:
     - Xác nhận farm hoàn toàn IDLE.
     - Lập tức kích hoạt lệnh chain đích (ví dụ: `python post_noon_chain_watchdog.py --force`).
  3. Ghi log đầy đủ telemetry (stdout + stderr) vào thư mục runtime:
     - `D:/Taadaa/runtime/kibe/cron-state/post_noon_waiter_<date>.log`
- Coordinator khởi chạy kịch bản này qua background process (`terminal(background=True)` hoặc `python.exe` detached).

## 3. Quy tắc Nghiệm thu & An toàn (Farm Invariants)
- **GATE 6 Media Evidence**: Luôn lấy 1 screencap O(1) từ máy canary đang online (`adb -s <serial> exec-out screencap -p > screencap_canary.png`) để đính kèm `MEDIA:<path>` ngay trong báo cáo điều phối, xác nhận farm online và sẵn sàng chuyển giao.
- **Không dry-run khi có yêu cầu chạy thật**: Chú ý cờ thực thi (`--live`, `--force`, không bật `--dry-run` trừ khi được yêu cầu rõ).
