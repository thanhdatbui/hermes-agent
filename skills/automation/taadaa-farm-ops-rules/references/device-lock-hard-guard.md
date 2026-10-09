# Quy Tắc Bảo Vệ Device Lock & Chống Can Thiệp Phá Hoại (Device Lock Hard Guard)

## 1. MÁY CÓ LOCK / TRẠNG THÁI LẠ = HANDS OFF (CẤM CAN THIỆP)
- Nếu thiết bị đang có lock active (`~/.codex/device-locks/machine_<N>.lock.json`) hoặc màn hình hiển thị trạng thái của một flow khác (ví dụ: màn hình Thiết lập 2FA, OTP, feed session, restore...):
  - **CẤM TUYỆT ĐỐI**: Tự tiện chạy `adb shell am force-stop` hoặc bấm `HOME` (keyevent 3).
  - **CẤM TUYỆT ĐỐI**: Tự tiện gọi `release_machine_reg_reservation` hoặc xóa file lock của tiến trình khác khi PID đó còn sống.
  - **CẤM TUYỆT ĐỐI**: Tự suy diễn "màn hình lạ = kẹt/treo" để tự ý dọn dẹp.
- Nguyên tắc phản xạ bắt buộc: `Doubt → Freeze → Report User → Wait`. Khi không chắc chắn: **LÀM ÍT HƠN, TUYỆT ĐỐI KHÔNG ĐƯỢC PHÁ HOẠI**.

## 2. QUYỀN GỌI LỆNH FORCE-STOP KHI TEST ĐỒ
- Lệnh `am force-stop` chỉ được phép thực thi trên máy khi và chỉ khi:
  1. Chính tiến trình hiện tại đã **acquire thành công `device_lock`** trên máy đó.
  2. PID chủ sở hữu lock trùng khớp với tiến trình gọi lệnh.
- Mọi hành vi dùng ADB thô từ Coordinator can thiệp vào máy của PID khác đều bị coi là phá hoại hệ thống.

## 3. CƠ CHẾ AUTO-REAP 1H LÀ SAFETY NET DUY NHẤT
- Hệ thống đã có watchdog `reap-dead-owner-locks.py` (TTL 3600s = 1 giờ).
- Nếu máy lock quá 1 giờ hoặc tiến trình chủ sở hữu đã chết (`owner_process_alive == False`):
  - Cron tự động chuyển file lock sang thư mục cách ly.
  - Cron tự động gọi `am force-stop` và bấm `keyevent 3` đưa máy về Home an toàn.
- Coordinator **KHÔNG ĐƯỢC PHÉP** can thiệp hay xóa lock trước thời hạn 1 giờ này.

## 4. BẮT BUỘC KHÓA CỨNG DEVICE_LOCK (CẤM BYPASS BẰNG ENV VAR)
- Mọi script can thiệp thiết bị (kể cả chạy lệnh CLI đơn lẻ như `social_reg_v1.py`) bắt buộc phải gọi `acquire_device_lock(user_authorized=True)`.
- Tuyệt đối cấm cờ bypass kiểu `DEVICE_LOCK_ENABLED` khiến script chạy lén mà không đăng ký lock với farm.
- Nếu không acquire được device lock -> Safe-Skip ngay lập tức.
