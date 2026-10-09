# Proactive ADB Hang Watchdog & tiktok_login_v1 CLI Flags

## 1. Proactive ADB Hang Watchdog (Chủ động xử lý khi Worker kẹt)
Khi dispatch worker thực hiện thao tác ADB / Login / Feed mà worker im lặng quá 2-3 phút hoặc log không nhích:
- **Triệu chứng**: Lệnh `inspect_machine.py` hoặc `adb shell` báo timeout (10s), `adb devices` treo không trả về kết quả.
- **Nguyên nhân**: `adb.exe` daemon trên host Windows bị deadlock ngầm (socket hang / pipe block giữa adb server và port 5037).
- **Hành động cấm**: CẤM Coordinator ngồi im chờ worker đụng trần timeout (600s/800s) rồi mới phát hiện.
- **Quy trình xử lý dứt điểm (O(1))**:
  1. Kiểm tra tiến trình: `ps -W | grep -i adb`
  2. Diệt tận gốc daemon treo: `taskkill -F -IM adb.exe`
  3. Khởi động lại sạch: `"C:\Program Files (x86)\xiaowei\tools\adb.exe" start-server`
  4. Ping kiểm tra lại thiết bị ngay: `python D:/Taadaa/tools/inspect_machine.py <N>`
  5. Tiếp tục luồng xử lý hoặc re-dispatch nếu worker đã bị abort.

## 2. CLI Flags Discipline: `tiktok_login_v1.py` vs `social_reg_v1.py`
- `tiktok_login_v1.py` có parser argparse riêng biệt, **KHÔNG** chấp nhận các cờ:
  - ❌ `--no-feed-after-reg`
  - ❌ `--no-avatar-after-reg`
  *(Nếu truyền các cờ này, argparse sẽ crash ngay với `error: unrecognized arguments` và exit code 2).*
- Để tắt feed/avatar hook trong login flow (kế thừa từ `social_reg_v1.py`), phải dùng **Environment Variables**:
  - `TIKTOK_REG_FEED_AFTER_REG=0`
  - `TIKTOK_REG_AVATAR_AFTER_REG=0`
- Cờ hợp lệ của `tiktok_login_v1.py`:
  `stt`, `--email <id/mail>`, `--all`, `--list`, `--resume`, `--ss`, `--no-track`, `--allow-parent-lock`, `--override-machine`, `--otp-only`.

## 3. Account Switcher Milestone Dialog Trap
- Khi vào trang Profile để mở Account Switcher, app TikTok có thể hiển thị dialog chúc mừng milestone:
  - Text: `Tổng số lượt thích` / `... đã nhận tổng cộng N lượt thích cho tất cả video`
  - Nút bấm: `OK`
- Dialog này làm mất hoặc che phủ header marker của username (`Header candidates=0` / `SWITCHER_NOT_CONFIRMED`), khiến workflow fail sang `MANUAL_REVIEW`.
- Giải pháp: Cần phát hiện và dismiss popup `Tổng số lượt thích` bằng cách tap vào `OK` hoặc click ngoài vùng trước khi scan switcher header.
