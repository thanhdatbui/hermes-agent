# Farm Lock Release & Test Artifact Safety (2026-08-24)

## 1. Test Artifact Isolation (Tránh báo máy ảo/test machine)
- **Vấn đề**: Khi unit test hoặc integration test chạy trên máy host (như test suite của `automation-core`, `Hotmail`, v.v.), các mock/dummy machine IDs (ví dụ: `machine=995`, serial giả lập) nếu tạo file lock trực tiếp trong thư mục production lock (`~/.codex/device-locks`) sẽ bị cron watchdog (`watch_device_locks.py`) quét trúng và báo động giả cho người dùng trên Telegram.
- **Quy chuẩn**:
  - Khi viết test hoặc script probe/dry-run, bắt buộc mock đường dẫn `lock_root` về thư mục tạm (ví dụ `tmp_path` trong pytest hoặc folder `tmp` riêng).
  - Tuyệt đối không ghi đè hoặc để rớt file lock test (`machine_99x.lock.json`) vào `C:\Users\Kibe\.codex\device-locks\`.
  - Nếu bắt buộc test live trên thư mục default, phải có khối `try...finally` dọn sạch cả cặp `machine_<ID>.lock.json` và `serial_<SERIAL>.lock.json` ngay lập tức.

## 2. Quy trình Mở khóa hàng loạt ("Mở khoá hết đống này" / "Unlock all")
Khi người dùng yêu cầu mở khóa tất cả các máy đang lock:
1. **Kiểm tra trạng thái PID / Process**:
   - Quét qua danh sách file lock trong `C:\Users\Kibe\.codex\device-locks\machine_*.lock.json`.
   - Đọc PID từ JSON và kiểm tra xem tiến trình giữ lock (ví dụ `PID 6544` - `tiktok-video`, `hotmail-change-info`, v.v.) còn sống hay đã kết thúc.
2. **Sao lưu trước khi gỡ (Backup Before Unlock)**:
   - Tạo thư mục backup định dạng: `C:\Users\Kibe\.codex\device-locks\backup_user_unlock_all_<YYYYMMDD_HHMMSS>`.
   - Di chuyển toàn bộ các file `.lock.json` vào thư mục backup.
3. **Xác nhận với Watchdog**:
   - Chạy lại watchdog `watch_device_locks.py` để verify output sạch: `Healthy: No active device locks found.`.
   - Báo cáo ngắn gọn cho người dùng: số lượng máy đã giải phóng, trạng thái tiến trình (PID) và xác nhận farm sạch lock.
