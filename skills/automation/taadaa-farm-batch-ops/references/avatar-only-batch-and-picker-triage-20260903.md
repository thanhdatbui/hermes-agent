# Avatar-Only Batch Execution & Picker Selection Triage (2026-09-03)

## 1. Standalone Avatar-Only Execution Flow
Khi cần cập nhật riêng Avatar cho danh sách máy cụ thể theo TikN (không đăng video, không ảnh hưởng trạng thái `Video Đã Đăng` trong workbook):

### Command Canonical:
```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "D:\Taadaa\Tiktok-video\run_tiktok_upload_avatar.ps1" `
  -Tik 3 `
  -AssignmentManifest "D:\CodexRuntime\tiktok-video\assignment-manifest-avatar.json" `
  -WorkerId hermes-kibe-avatar `
  -ForceAvatarMachineList "35,41,64,65,74,75,76,77,78,79,80" `
  -MaxParallel 40 `
  -HostConfigPath "D:\Taadaa\machine-config\kibe.yaml"
```

### Yêu cầu bắt buộc trước khi launch:
1. **Assignment Manifest Sync**: Bắt buộc cập nhật danh sách máy vào `resources: ["machine:<N>", ...]` trong `D:\CodexRuntime\tiktok-video\assignment-manifest-avatar.json`.
2. **Khung giờ chạy**: Chỉ chạy sau khi ca nuôi kết thúc (sau 10:30 Ca 1, 16:30 Ca 2, 00:30 Ca 3) để tránh xung đột UI và device-lock với cron `phase9-runner-tiktok-feed`.

---

## 2. Triage "Up ava sai" vs "ACCOUNT_MISSING"
Khi nhận phản hồi "up ava sai" hoặc nghi ngờ avatar tạo ra bị lỗi:
1. **Kiểm tra file đĩa trước**:
   - Nguồn gốc: `D:\video goc\<video gốc>\avatar.jpg` (kích thước chuẩn 512x512 RGB JPEG).
   - Nguồn render: `D:\TIKTOK-videonuoinick\<Folder Video>\avatar.jpg`.
2. **Kiểm tra log batch trước đó**:
   - Nếu log ghi `ACCOUNT_SWITCHER: select account failed: ACCOUNT_MISSING`: Workflow đã dừng ở bước chuyển nick, **chưa từng bước vào `ENSURE_AVATAR`**, avatar trên TikTok vẫn là avatar cũ/chưa up chứ không phải file tạo ra bị sai.

---

## 3. Photo Picker Next Button & Fallback Tap
- Trong màn hình Photo Picker của TikTok:
  - Khi script tap vào tile ảnh đầu tiên `(6, 222, 269, 488)`, các selector tìm nút "Tiếp" (`o_9`, `wrj`, `Tiếp (1)`) có thể không khớp ngay do TikTok đổi resource-id.
  - Sau chuỗi wait-timeout, script tự động fallback tap vào tọa độ nút Tiếp hiển thị trực quan: `(924, 1842)` (`[ENSURE_AVATAR] Selection screen remained; tapping visible Next button`).
  - Sau khi tap `(924, 1842)`, màn hình Cắt/Crop mở ra, script tự động bỏ tick "Đăng ảnh này lên Nhật ký" và tap "Lưu" để hoàn tất.
