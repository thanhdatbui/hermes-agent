# AI Auto-Recovery Emergency Rollback & ViChanger Broadcast Timeout Diagnosis (2026-08-20)

## 1. Cơ Chế Emergency Rollback trong AI Auto-Recovery (`code_patcher.py`)
- **Nguyên lý hoạt động**:
  - Khi AI Auto-Recovery sinh code patch và commit thành công (SHA ghi vào `D:\Taadaa\runtime\kibe\recovery_patch_counter.json`), hệ thống mở cửa sổ theo dõi 15 phút (`ROLLBACK_WINDOW_SECONDS = 900`).
  - Mỗi khi có alert lỗi cùng signature gửi về, hàm `record_alert()` ghi nhận timestamp.
  - Nếu trong vòng 15 phút phát sinh $\ge 3$ alerts (`ROLLBACK_THRESHOLD = 3`), hàm `attempt_rollback()` tự động kích hoạt:
    1. Thực thi `git revert --no-edit HEAD` trên branch `master`.
    2. Tự động `git push origin master` để đồng bộ hoàn nguyên toàn farm.
    3. Bắn tin cảnh báo `🚨 [EMERGENCY ROLLBACK]` vào Telegram group Farm Alerts.
    4. Xóa key trong `recovery_patch_counter.json`.
- **Quy trình kiểm tra khi gặp cảnh báo Emergency Rollback**:
  - Kiểm tra `git status` và `git log -n 5` trên repo `tiktok-luot nuoi acc`.
  - Đọc `recovery_patch_counter.json` để đối soát các signature lỗi và commit SHA liên quan.
  - Đảm bảo working tree sạch, không bị dính file conflict hoặc uncommitted edits dở dang.

## 2. Xử Lý Lỗi ViChanger GET_IP Broadcast Timeout
- **Hiện tượng**:
  - Script preflight / VPN gate báo lỗi: `ViChanger GET_IP broadcast exception: adb command timed out: ('adb.exe', '-s', '<SERIAL>', 'shell', 'am', 'broadcast', '-a', 'vn.vichanger.app.GET_IP', '-n', 'vn.vichanger.app/.AdbCaller')`.
  - Script tạm dừng và giữ hiện trường.
- **Quy trình chẩn đoán & xác minh**:
  1. Kiểm tra interface mạng trên thiết bị: `adb -s <SERIAL> shell ip a` xem `tun0` có trạng thái `UP` và có IP (`inet 172.19.0.1/30` hoặc tương đương) hay không.
  2. Gửi lại lệnh broadcast đơn lẻ: `adb -s <SERIAL> shell am broadcast -a vn.vichanger.app.GET_IP -n vn.vichanger.app/.AdbCaller`. Nếu trả về `result=0` thì ViChanger service vẫn đang hoạt động, timeout trước đó là do nghẽn ADB tạm thời.
  3. Chụp màn hình qua ADB (`screencap -p`) và đọc qua `vision_analyze` để xác nhận màn hình thực tế (tránh nhầm lẫn trạng thái Home với ứng dụng bên thứ ba như Outlook/TikTok).
