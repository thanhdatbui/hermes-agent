# Android 8 Dynamic Forward Port & Service Recovery (2026-08-21)

## 1. Dynamic Port Forwarding (Tránh Tranh Chấp Đa Thiết Bị)
- Daemon `atx-agent` lắng nghe tại port 7912 trên mỗi thiết bị Android.
- Phía PC: BẮT BUỘC dùng lệnh `adb forward tcp:0 tcp:7912` để PC tự cấp một Local Dynamic Port ngẫu nhiên (vd: 54123, 54124...) cho từng serial/máy.
- TUYỆT ĐỐI CẤM dùng chung một port cứng (như 7912) trên PC cho toàn farm vì sẽ gây race condition / dump nhầm màn hình giữa các máy chạy song song.

## 2. Khắc Phục SHELL_EXIT_137 / Background Service Trên Android 8
- Trên Android 8+, lệnh `am startservice` khi ứng dụng không ở foreground sẽ bị chặn (`Error: app is in background`).
- Khi gặp mã thoát `EXIT 137` (SIGKILL do Android Low Memory Killer) hoặc service uiautomator bị rơi:
  - Khởi động lại service bằng `monkey`: `adb shell "monkey -p com.github.uiautomator 1"`.
  - Khởi động lại toàn bộ ATX daemon: `adb shell "pkill -9 -f atx-agent; am force-stop com.github.uiautomator"` rồi chạy `/data/local/tmp/atx-agent server -d`.
  - Luôn sử dụng ATX-primary JSON-RPC session dump thay cho shell `uiautomator dump` để tránh dính idle state error và OOM kill.
