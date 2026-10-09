# Quy Chuẩn Đồng Bộ Vòng Đời Profile GPM & Thiết Bị S7 (Lifecycle Sync & Safety Standards)

## 1. Đồng bộ Bộ Lọc An Toàn Tạo Profile (Safety Candidate Filtering)
Khi tự động tạo profile GPM từ dữ liệu Farm S7 (`master_gmail_manager.xlsx`), bắt buộc phải áp dụng đầy đủ các bộ lọc tương đương `batch_create_farm_gpm_profiles.py`:
- **Trạng thái LIVE**: Chỉ chọn tài khoản có cột `Trạng Thái == "LIVE"`.
- **Loại trừ 'khoale'**: Bỏ qua nếu email hoặc recovery email chứa `khoale`.
- **Loại trừ Status Pipeline**: Kiểm tra `oauth_pipeline_status.json`, loại trừ các email nằm trong:
  - `omniroute_success`
  - `excluded_khoalee`
  - `wrong_password_or_checkpoint`
- **Kiểm tra trùng lặp GPM SQLite DB**:
  - Không chỉ kiểm tra cột `Name` mà phải trích xuất regex email từ cả `Name` và `JsonData` trong bảng `Profiles` (`profile_data.db`).
- **Kiểm tra S7 Online qua ADB**:
  - Đối chiếu `Số Máy Farm` -> lấy Serial từ `PROXYgandienthoai.xlsx` (sheet `Proxy`).
  - Chạy `adb devices` và chỉ tạo profile khi thiết bị S7 tương ứng đang ở trạng thái `device` online.
- **Chống trùng lặp trong sheet**: Duy trì `seen_emails` trong quá trình duyệt danh sách.

## 2. Dọn Dẹp Thiết Bị S7 Cuốn Chiếu (Rolling Cleanup Gate)
- **Khung giờ buổi sáng**: Chỉ chạy trong khung giờ an toàn 07:15 - 08:45 (HCM timezone `Asia/Ho_Chi_Minh`) để không xung đột với giờ vận hành cao điểm.
- **Manifest Slot Check**:
  - Đọc manifest ca nuôi gần nhất (`runtime/kibe/cron-state/manifests`).
  - Bỏ qua máy nếu máy đang trong slot feed hoặc có slot nuôi sắp diễn ra trong vòng 30 phút (`slot_time <= now < slot_end` hoặc `now <= slot_time < now + 30m`).
- **Non-blocking Device Lock**:
  - Bắt buộc dùng `acquire_device_lock(machine, serial, project="gpm-cleanup")`. Nếu `DeviceLockUnavailable`, bỏ qua sang máy khác ngay lập tức, không block luồng.

## 3. Quy chuẩn Telemetry & Logging
- Thiết lập format log chuẩn: `%(asctime)s [%(levelname)s] %(message)s`.
- Ghi đồng thời ra file log `logs/sync_gpm_lifecycle.log` và `sys.stdout`.
- **Nghiêm cấm nuốt lỗi im lặng**: Không dùng `except Exception: pass`. Phải ghi nhận cảnh báo hoặc lỗi bằng `logger.warning(...)` / `logger.error(...)` có kèm context (email, machine_id, exception).

## 4. Kiểm Thử Unit Test (Isolated Unit Tests)
- Kiểm thử cô lập bằng mock cho:
  - `is_morning_cleanup_window()`: mock datetime trong và ngoài khung giờ 07:15 - 08:45.
  - `is_machine_in_feed_slot()`: mock thư mục manifest và cấu trúc JSON slot nuôi.
  - `cleanup_s7_die_accounts()`: kiểm tra dry-run không gọi lệnh ADB xóa thật.
  - Chạy test thông qua `python -m pytest tests/test_sync_gpm_lifecycle.py -v`.
