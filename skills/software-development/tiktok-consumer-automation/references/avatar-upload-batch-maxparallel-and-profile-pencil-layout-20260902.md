# TikTok Avatar Upload: MaxParallel 40, Pencil Icon Layout & Story Checkbox (2026-09-02)

## 1. Canonical Runner & Batch Concurrency
- **Repo:** `D:\Taadaa\Tiktok-video`
- **Canonical script:** `run_tiktok_upload_avatar.ps1` (hoặc `run_tiktok_upload_batch.ps1 -AvatarOnly -Tik <N>`).
- **Yêu cầu MaxParallel:** Max worker khi chạy batch upload avatar trên farm là **40** (`-MaxParallel 40`). Trong `run_tiktok_upload_batch.ps1`, param `$MaxParallel` phải cấu hình `[ValidateRange(1, 40)]`.

## 2. Layout Nút Sửa Hồ Sơ (Pencil Icon) & Cuộn Top Profile
- **Hiện tượng:** Sau khi chạy kiểm tra/scan video baseline trên trang Hồ sơ, màn hình Profile bị scroll dở khiến nút Sửa hồ sơ bị trôi mất. Fallback deeplink `snssdk1233://profile/edit` bị TikTok chặn cảnh báo popup *"Hoạt động không có sẵn"*.
- **Xử lý:**
  1. Luôn thực hiện swipe cuộn lên đỉnh trang Profile trước khi vào luồng avatar:
     `adb.shell(['input', 'swipe', '540', '400', '540', '1500', '300'])`
  2. Bắt nút Sửa hồ sơ dạng icon bút chì (bounds `[750, 480][950, 620]`, center `(849, 552)` hoặc `(871, 552)`) cạnh username/display name.

## 3. Màn hình Crop & Bẫy Story Checkbox ("Đăng ảnh này lên Nhật ký")
- **Layout màn hình Crop:**
  - Checkbox: `Đăng ảnh này lên Nhật ký` (`id/sca` tại bounds `[48, 1554][120, 1626]`, center `(84, 1590)`).
  - Nút Hủy: bounds `[48, 1728][528, 1860]`
  - Nút Lưu / Lưu và đăng: bounds `[552, 1728][1032, 1860]` (center `(792, 1794)`).
- **Thao tác chuẩn:**
  1. Bỏ chọn checkbox story nếu đang check (`checked="true"`): tap `(84, 1590)` để tránh đăng avatar thành story.
  2. Tap nút Lưu tại `(792, 1794)` (hoặc `Lưu và đăng` tại `(540, 1764)`).

## 4. Coordinate Fallback & Tọa độ Mở Account Switcher Top-Left (140, 300)
- **Adapter hook:** Trong `scripts/tiktok_workflow/adapter.py`, cài đặt `coordinate_fallback(self, action="switcher") -> (540, 552)` để fallback khi core `account_switcher` gặp `SWITCHER_ANCHOR_AMBIGUOUS`.
- **Top-left name anchor:** Trên layout TikTok 46.x có username/display name nằm ở góc trên bên trái (`id/sv6` / `id/su7`, bounds `[36, 249][260, 364]`), tap trực tiếp vào `(140, 300)` để mở bảng trượt `Chuyển đổi tài khoản`.
