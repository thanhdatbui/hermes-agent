# Asymmetric Device Lock Antipattern & Healer Collision Invariants

## 1. Bản Chất Sự Cố "Hàng Loạt Máy Đóng/Mở Lại TikTok & Đổi Nick" (2026-10-18)
- **Hiện tượng:** User quan sát thấy farm đang yên ổn thì đột ngột hàng chục máy Galaxy S7 đồng loạt bị `force-stop` sập TikTok, mở lại TikTok, rồi tự động mở menu Account Switcher chuyển sang tài khoản khác.
- **Nguyên nhân gốc rễ (Root Cause):**
  1. **Anti-pattern "Chỉ đọc lock mà không tạo lock" (Asymmetric Lock):**  
     Script `tiktok_rename_rolling_watchdog.py` có hàm `get_locked_machines()` để bỏ qua các máy đang bận. Tuy nhiên, khi bốc 25 máy rảnh (`MAX_WORKERS = 25`) để thi công, script **KHÔNG HỀ GỌI `acquire_device_lock`** để đăng ký khóa thiết bị cho chính nó trong `~/.codex/device-locks`.
  2. **Xung đột trực tiếp với Watchdog Dọn Rác (`farm-idle-screen-and-app-healer.py`):**  
     Cả hai watchdog đều chạy chu kỳ 15 phút (`*/15 * * * *`). Khi `farm-idle-screen-and-app-healer` thức dậy, nó quét toàn farm: máy nào **không có file lock active** mà TikTok đang mở trên màn hình thì lập tức phát lệnh:
     `am force-stop com.ss.android.ugc.trill` và `input keyevent 3` (về HOME).
  3. **Vòng lặp đá nhau (Race Condition):**  
     Trong worker đổi tên (`do_rename_canonical_runner.py`), bước khởi đầu luôn là `am force-stop` + `monkey` mở lại app. Khi app mở lên mà không có lock, healer dập tắt app; rename worker thấy app sập lại cố mở lại và mở Account Switcher để tìm nick mục tiêu. Tạo thành chuỗi thao tác giật cục, chớp tắt hàng loạt máy trên farm.

## 2. Hard Invariants Phòng Ngừa Xung Đột Cho Consumer

1. **Nguyên tắc "Đụng thiết bị = Bắt buộc giữ Lock" (No-Lock No-Touch):**
   - CẤM TUYỆT ĐỐI bất kỳ consumer/script nào (kể cả tác vụ phụ như Rename, Avatar, 2FA, Clear cache, Diagnostics) gửi lệnh ADB can thiệp giao diện/app (`am force-stop`, `monkey`, `input tap`, `input keyevent`) mà không bọc trong context manager của `automation-core`:
     ```python
     from automation_core.device_lock import acquire_device_lock

     with acquire_device_lock(machine=str(mid), serial=serial, project="tiktok-rename"):
         # Thực thi thao tác ADB
     ```
   - Việc chỉ kiểm tra lock ở bước lọc danh sách (read-only pre-filter) là **hoàn toàn vô nghĩa** nếu không claim lease khi chạy thực tế.

2. **Quy chuẩn Healer Safe-Guard:**
   - Trong các watchdog dọn dẹp nền (`farm_idle_screen_and_app_healer.py`), hàm nhận diện `get_locked_devices()` phải parse chuẩn cả hai định dạng alias:
     - `machine_{mid}.lock.json`
     - `machine_{mid}.{serial}.lock.json` (dùng regex `re.search(r"machine_(\d+)", lf.name)` thay vì `replace().isdigit()`).

3. **Kỷ luật Khung giờ Tác vụ Phụ (Auxiliary Cron Windows):**
   - Các tác vụ đổi tên rolling, up avatar, bật 2FA chỉ được phép chạy khi:
     - Không trùng slot bắt đầu các ca nuôi chính (né mốc 00:00, 06:00, 12:00, 18:00 ít nhất 15 phút).
     - Giới hạn số worker an toàn (`max_workers <= 5-10`), cấm bung đồng loạt `25-30` workers cướp bus ADB và gây sốc điện/mạng cho farm.
