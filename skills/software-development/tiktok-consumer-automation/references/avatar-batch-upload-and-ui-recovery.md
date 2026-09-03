# TikTok Avatar Upload & Batch Avatar-Only Operations

## 1. Canonical Scripts & Commands
Trong repo `D:\Taadaa\Tiktok-video`:
- Script chuyên dụng: `run_tiktok_upload_avatar.ps1`
- Hoặc qua batch launcher: `run_tiktok_upload_batch.ps1 -AvatarOnly -ForceAvatarMachineList "<list_machines>" -Tik <N> -MaxParallel <N>`

**Ví dụ chạy toàn bộ row:**
```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "D:\Taadaa\Tiktok-video\run_tiktok_upload_avatar.ps1" `
  -Tik 3 `
  -AssignmentManifest "D:\CodexRuntime\tiktok-video\assignment-manifest-avatar-tik3.json" `
  -WorkerId "hermes-kibe-avatar" `
  -ForceAvatarMachineList "1,2,3,...,76" `
  -MaxParallel 10
```

## 2. Các Pitfalls & Fixes đã encode
1. **Trôi Profile sau bước scan baseline video (`ACCOUNT_READY`):**
   - *Hiện tượng:* Script scan cuộn lưới video trên Profile khiến màn hình dừng ở lửng trang, nút "Sửa hồ sơ" bị trôi mất. Fallback deep-link `snssdk1233://profile/edit` bị TikTok chặn báo *"Hoạt động không có sẵn"*.
   - *Fix:* Luôn thực hiện swipe đưa Profile về đỉnh (`swipe 540 400 540 1500`) trước khi tìm nút Sửa hồ sơ hoặc bút chì.
2. **Layout nút Sửa hồ sơ mới:**
   - TikTok layout mới có nút bút chì tại vị trí `[777,510][921,594]` (center `849, 552`) và loại trừ các icon tab video/thích hoặc icon "Tạo" (`ct8`).
   - Màn hình Sửa hồ sơ được nhận diện bằng cả `Thay đổi ảnh` / `Change photo`.
3. **Nút "Tiếp" trên Image Picker mới:**
   - Trên một số build TikTok mới, nút "Tiếp" sau khi chọn ảnh có resource-id `xip` bên cạnh `o_9` và text `Tiếp (1)`.
