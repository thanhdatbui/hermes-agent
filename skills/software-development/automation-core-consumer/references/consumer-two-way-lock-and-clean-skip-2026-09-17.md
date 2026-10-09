# Two-Way Device Lock & Clean Skip Contract for Consumers (2026-09-17)

## Bối cảnh
Khi consumer vận hành chạy batch trên nhiều máy (ví dụ `multi-machine-feed-session`), operator có thể lock máy đột xuất để chạy script can thiệp/bảo trì. Ngược lại, khi ca nuôi đang chạy, script can thiệp ngoài band phải chờ ca nuôi kết thúc.

## Consumer Rules

### 1. Preflight Launcher (PowerShell / Shell)
- Tuyệt đối không xây dựng `$machineList` trước khi kiểm tra trạng thái lock.
- Trong vòng lặp kiểm tra lock:
  - Nếu lock file tồn tại và process PID còn sống: Bỏ qua máy đó, KHÔNG đưa vào danh sách `$machineList`.
  - Nếu lock file tồn tại nhưng PID đã chết (stale lock): Xóa file lock và đưa máy vào danh sách chạy bình thường.
  - Nếu toàn bộ danh sách máy đều bị lock: Thoát an toàn (`exit 0` / Clean Exit), không xem đó là lỗi hệ thống.

### 2. Batch Aggregator (`_aggregate_rows`)
- Không gom chung `needs-user-decision` và `skipped-device-locked` vào một nhánh lỗi.
- `needs-user-decision`: Giữ `ExitStatus.MANUAL_NEEDED` vì đây là trường hợp xung đột quyền sở hữu cần người xử lý.
- `skipped-device-locked`: Là trạng thái bỏ qua hợp lệ do máy đang bận tác vụ khác.
  - Nếu có máy hoàn thành `success` hoặc `degraded` và một số máy `skipped-device-locked`: Toàn batch nhận `ExitStatus.SUCCESS` với thông báo "completed with some locked machines cleanly skipped".
  - Chỉ khi 100% máy trong batch bị `skipped-device-locked` mới trả về `ExitStatus.MANUAL_NEEDED`.

### 3. Operator CLI Wrapper
Sử dụng wrapper `D:/Taadaa/tools/with_device_lock.py` để bọc mọi lệnh can thiệp ad-hoc:
```bash
python D:/Taadaa/tools/with_device_lock.py --machine <N> -- <command...>
```
Giúp tránh hoàn toàn việc tranh chấp ADB hoặc xung đột UI với các session automation đang chạy.
