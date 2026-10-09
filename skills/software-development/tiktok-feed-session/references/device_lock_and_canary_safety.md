# Quy tắc Kiểm tra Device Lock & B4 Canary Safety

## 1. Ngăn chặn xung đột Device Lock (Active vs Stale Lock)
- **Vị trí lock file:**
  - `C:\Users\Kibe\.codex\device-locks\machine_<N>.lock.json`
  - `C:\Users\Kibe\.codex\device-locks\serial_<serial>.lock.json`
- **Nguyên tắc an toàn tối thượng:**
  - File lock chỉ được coi là **STALE** khi và chỉ khi PID ghi trong file lock **không còn tồn tại** trên hệ thống (tiến trình đã kết thúc/bị crash đột ngột mà chưa giải phóng lock).
  - Trước khi xóa lock, BẮT BUỘC kiểm tra trạng thái PID:
    ```powershell
    Get-Process -Id <PID> -ErrorAction SilentlyContinue
    ```
  - **CẤM TUYỆT ĐỐI** xóa file lock nếu PID vẫn đang chạy (Active Process). Đặc biệt khi một batch lớn (`run_tiktok.py --mode multi-machine-feed-session`) đang vận hành song song nhiều máy, tiến trình cha nắm lock để điều phối từng máy theo cohort/worker.
  - Xóa lock khi PID còn sống sẽ làm cho runner thứ hai (ví dụ Canary Test) chiếm thiết bị, gửi lệnh ADB song song, gây tranh chấp ADB và làm fail cả hai phiên chạy.

## 2. Kiểm tra log hiện trường trước khi can thiệp
- Khi PID đang sống, kiểm tra trực tiếp file log của thiết bị tương ứng:
  `D:\Taadaa\runtime\kibe\live\<date>\<run-id>\machines\machine_<N>\<run-id>\log.jsonl`
- Đọc tail của file log để xác định máy đang ở step nào (ví dụ: `profile_preflight_switch`, `account-switcher`, `profile_preflight_verify_identity`, `feed_swipe`).
- Nếu máy đang hoạt động bình thường, thông báo cho user và chờ batch hoàn thành thay vì cưỡng bức kill hoặc xóa lock.
