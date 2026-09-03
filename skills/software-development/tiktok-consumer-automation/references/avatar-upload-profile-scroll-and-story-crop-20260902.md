# Avatar Upload Profile Scroll, Deep-link Anti-fraud & Story Crop Handling (2026-09-02)

## 1. Hiện tượng & Phát hiện

### A. Nút Bút Chì Sửa Hồ Sơ & Lỗi Trôi Nút do Profile Grid Scroll
- Trên giao diện TikTok mới trên farm Samsung Galaxy S7 (1080x1920), nút Sửa hồ sơ nằm ngay bên phải tên hiển thị `su7` dưới dạng icon bút chì, bounds `[777,510][921,594]` / `[799,510][943,594]` (tâm `(849, 552)` hoặc `(871, 552)`).
- Khi bước `ACCOUNT_READY` thực hiện scan cuộn lưới video (`PROFILE_GRID` viewports), màn hình Profile bị giữ lại ở vị trí lửng bên dưới khiến nút bút chì trôi khỏi viewport hiển thị.
- **Khắc phục chuẩn:** Trước khi vào phân loại hoặc tìm nút sửa hồ sơ trong `ENSURE_AVATAR`, bắt buộc phải vuốt kéo trang Profile về đỉnh (2 lần `adb shell input swipe 540 400 540 1500 300`) để nút bút chì hiển thị trọn vẹn trong XML.

### B. Bẫy Deep-link `snssdk1233://profile/edit` trên Tài Khoản Phụ
- Khi không tìm thấy nút sửa hồ sơ, nếu script fallback sang intent deep-link `am start -a android.intent.action.VIEW -d snssdk1233://profile/edit -p com.ss.android.ugc.trill`, TikTok sẽ phát hiện hành vi mở màn hình setting trên tài khoản phụ (secondary account) và bật popup cảnh báo:
  > *"Hoạt động không có sẵn. Để tiếp tục tham gia vào các hoạt động, hãy chuyển sang tài khoản ban đầu mà bạn đã dùng trên thiết bị này."*
- Popup này làm `_wait_for_avatar_edit_screen` nhận diện `unavailable` và fail-closed workflow.
- **Khắc phục chuẩn:** Loại bỏ hoặc không kích hoạt deep-link trên tài khoản phụ; luôn dùng semantic click / tọa độ verified `(849, 552)` trên Profile root đã cuộn về top.

### C. Màn hình Cắt Ảnh (Crop), Checkbox Story & Nút "Lưu và đăng"
- Sau khi chọn ảnh từ Photo Picker, TikTok chuyển sang màn hình Cắt ảnh (`Cắt`):
  - Checkbox *"Đăng ảnh này lên Nhật ký"* nằm tại bounds `[48,1554][120,1626]` (tâm `(84, 1590)`, `id/sca`). Phải tap để bỏ tick trước khi lưu.
  - Nút lưu avatar trên layout mới là nút *"Lưu và đăng"* hoặc *"Lưu"* tại bounds `[552,1728][1032,1860]` (tâm `(792, 1794)`) hoặc `[96,1698][984,1830]` (tâm `(540, 1764)`).

## 2. Vận hành Batch Upload Avatar

- Launcher canonical tách riêng upload avatar:
  ```powershell
  powershell.exe -NoProfile -ExecutionPolicy Bypass -File "D:\Taadaa\Tiktok-video\run_tiktok_upload_avatar.ps1" `
    -Tik 3 -AssignmentManifest "D:\CodexRuntime\tiktok-video\assignment-manifest-avatar-tik3.json" `
    -WorkerId "hermes-kibe-avatar" `
    -ForceAvatarMachineList "1,2,3...76" `
    -MaxParallel 40
  ```
- `run_tiktok_upload_batch.ps1` hỗ trợ `-MaxParallel` lên đến 40 worker (`ValidateRange(1, 40)`).

## 3. Virtualenv Isolation khi chạy Reconcile / Login
- Khi chạy script login / reconcile `reconcile_tiktok_accounts.py` từ terminal git-bash hoặc subshell, luôn xóa biến `PYTHONPATH` (`env -u PYTHONPATH`) để interpreter `tiktok-reg-recovery\Scripts\python.exe` không nạp chéo thư viện từ venv agent dẫn đến lỗi `ImportError: cannot import name '_imaging' from 'PIL'`.
