# Gateway Pre-Tool Guard File Lock Deadlock & PID-Alive Trap

## 1. Bản chất sự cố (Root Cause)
Khi một plugin guard hoặc pre-tool hook giành file lock chung, hệ thống dễ rơi vào deadlock toàn diện nếu:
1. **Thiếu giải phóng bất biến (finally):** Hook gặp early-return (như bị chặn bởi Blacklist/Guard Self-Protection), Exception hoặc crash đột ngột khiến file handle bị process Python giữ chặt.
2. **Bẫy PID-Alive Stale Lock:** Logic kiểm tra stale lock cũ chỉ tự động bẻ lock khi PID ghi trong lock đã CHẾT (`not psutil.pid_exists(pid)`). Nhưng nếu chính Gateway Hermes (PID đang chạy) bị rò rỉ lock trong RAM, PID này luôn SỐNG! Hệ thống không bao giờ tự gỡ lock, dẫn đến mọi tool call tiếp theo đều bị chặn với lỗi fail-closed sau timeout 3s.
3. **Catch-22 Tự trói tay chân:** Khi tool call bị chặn bởi hook pre-tool, coordinator không thể gọi bất kỳ công cụ nào (kể cả Claude CLI, terminal, read_file) từ bên trong để tự giải cứu do hook chạy trước mọi lệnh.

## 2. Giải pháp kỹ thuật chuẩn hóa (4 tầng bảo vệ)
1. **Lock quá 10s tự động bẻ:** Bất kể PID chủ còn sống hay chết, nếu file lock đã tồn tại > 10 giây thì bị coi là rò rỉ và tự động gỡ (`os.remove` / ghi đè).
2. **Xử lý lock cùng PID:** Nếu lock ghi PID của chính tiến trình hiện tại nhưng không còn thread nào giữ khóa nội bộ, tự động giải phóng sau 1 giây.
3. **Khóa luồng `threading.Lock()`:** Đồng bộ giữa các worker/thread trong cùng process để triệt tiêu xung đột file lock.
4. **Giải phóng bất biến trong `finally`:** Toàn bộ logic kiểm tra và file lock bắt buộc nằm trong khối `try ... finally` giải phóng cả file lock và `threading.Lock()` ngay lập tức, bất kể exception hay return sớm.

## 3. Khởi động lại Gateway sau khi vá code plugin
Khi sửa file plugin của Hermes, mã nguồn trong RAM của Gateway không tự động reload:
- Chạy watcher nền khi idle: `powershell -ExecutionPolicy Bypass -File D:\Taadaa\Hermes\deploy\hermes-home\scripts\restart-when-idle.ps1`.
- Hoặc chạy từ shell bên ngoài Gateway: `hermes gateway restart`.
