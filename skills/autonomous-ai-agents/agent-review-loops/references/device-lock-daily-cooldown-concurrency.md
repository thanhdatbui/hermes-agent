# Device Lock & Daily Reg Cooldown Multi-Process Locking Patterns

## 1. Vấn đề tranh chấp file JSON (Race Condition)
Khi farm chạy 40–80 worker đồng thời:
- Nếu dùng pattern đọc-sửa-ghi (`_read_json` -> sửa -> `_atomic_write_json`) không có lock thì các process ghi đè làm mất bản ghi cooldown của nhau (Lost Update).
- `threading.Lock` chỉ có tác dụng trong cùng một process Python, không khóa được giữa các process độc lập.

## 2. Giải pháp Kernel File Locking chuẩn hệ điều hành
Sử dụng file lock riêng dạng `.flock` kết hợp:
- **Windows:** `msvcrt.locking(fileno, msvcrt.LK_NBLCK, 1)`
- **POSIX/Linux:** `fcntl.flock(fileno, fcntl.LOCK_EX | fcntl.LOCK_NB)`

### Lưu ý sống còn trên Windows:
1. File `.flock` bắt buộc phải được ghi sẵn **ít nhất 1 byte** (`b"0"`) khi khởi tạo. Nếu file rỗng 0-byte, hàm `msvcrt.locking(..., 1)` sẽ thất bại vì không thể khóa vùng byte vượt quá EOF (`PermissionError`/`OSError`).
2. Mở file ở chế độ binary read/write: `open(path, "r+b")`.
3. Nhả lock bằng `locked_file.seek(0)` rồi `msvcrt.locking(..., msvcrt.LK_UNLCK, 1)`.

## 3. Quy tắc Check-and-Reserve cho Cooldown 1 máy/1 lần/ngày
- Trước khi chạy: Kiểm tra `is_machine_reg_cooldown_active(stt)` -> nếu có thì fail-closed dừng ngay.
- Đăng ký giữ chỗ (Reservation): Khi bắt đầu luồng `register()`, phải đặt cọc trạng thái `running/reserved` trong lock file để các worker khác cùng STT không vượt qua check.
- Ghi nhận chính thức: Khi có `VERIFIED_SUCCESS`, ghi `cooldown_until` (hết ngày hiện tại) vào `reg_daily_cooldowns.json`.
- Fail-Closed parsing: Luôn parse ISO date đầy đủ bằng `date.fromisoformat()` hoặc `datetime.fromisoformat()`. Nếu payload JSON corrupt/lỗi type thì fail-closed hoặc khôi phục về schema an toàn.
