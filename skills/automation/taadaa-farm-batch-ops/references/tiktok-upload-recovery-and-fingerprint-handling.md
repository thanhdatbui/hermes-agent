# Quy Tắc Xử Lý Recovery UI Upload & Quản Lý Fingerprint (2026-08-26)

## 1. Bản chất sự cố chạy đè Batch Upload khi Feed chưa dứt điểm
- **Hiện tượng:** Khi nhịp chạy vét cuối của Phiên 3 (`row-1-231528` / `row-1-001531`) vẫn đang lướt feed muộn trên một số máy, việc kích hoạt `run_tiktok_upload_batch.ps1` chạy song song sẽ làm 2 luồng cùng tương tác trên 1 thiết bị:
  - Luồng Feed đang cố điều hướng về Home / Profile (`tap_home` / `tap_profile`).
  - Luồng Upload mở app, đẩy file video MP4 và cố vào picker.
- **Hậu quả:** Gây văng focus TikTok ra màn hình chính (`TikTok focus lost`), mở nhầm màn hình Camera/Media Picker (`camera_creation_overlay`) và kích hoạt Farm Alerts giả mạo.

## 2. Quy trình Recovery Upload chuẩn qua Script
Khi cần xử lý (fix) các máy bị lỗi UI / kẹt màn hình / mất focus:
1. **Kiểm tra trạng thái Feed:** Bắt buộc xác nhận toàn bộ worker của feed session đã kết thúc hoàn toàn.
2. **Khởi chạy Recovery Mode bằng Script Canonical (CẤM SỬA TAY):**
   ```powershell
   powershell.exe -NoProfile -ExecutionPolicy Bypass -File "D:\Taadaa\Tiktok-video\run_tiktok_upload_batch.ps1" -Tik <N> -Confirmation RUN -RecoveryMode -AllowDeviceRebootRecovery
   ```
   - Cờ `-RecoveryMode`: Tự động nhận diện các máy chưa `post_verified` và thử lại đúng video tiếp theo.
   - Cờ `-AllowDeviceRebootRecovery`: Tự động soft-reboot app/thiết bị khi gặp kẹt UI/ATX session.
3. **Bỏ qua máy Offline:** Bỏ qua các máy mất kết nối ADB / USB cáp (`61, 62, 63, 74`) và các máy trống nick (`75, 77, 78, 79, 80`).
4. **Xử lý Media Fingerprint Pending & Tránh chạy đè:**
   - Nếu worker bị crash/kill để lại file `reserved` trong `D:\CodexRuntime\tiktok-video\idempotency\media-fingerprints\<key>.json`, script recovery sẽ tự động giải phóng các reservation của worker chết nếu quá stale timeout hoặc dọn dẹp trước khi thử lại.
5. **Nguyên tắc Encode Code:** Mọi bản vá logic trong quá trình recovery (decouple timeout budget, fallback import popup handlers, location dialog dismissals) phải được commit và review APPROVED lên Git codebase trước khi triển khai, không chạy tay tùy tiện.
