# Avatar Batch Upload, Profile Scroll Drift, and Switcher Fallback (2026-09-02)

## 1. Avatar Upload Batch Launcher (`run_tiktok_upload_avatar.ps1`)
- **MaxParallel Parameter**: Farm mặc định hỗ trợ chạy tới 40 workers (`-MaxParallel 40`). Trong `run_tiktok_upload_batch.ps1`, attribute validate range phải là `[ValidateRange(1, 40)]` thay vì giới hạn cũ 30.
- **Standalone Command**:
  ```powershell
  powershell.exe -NoProfile -ExecutionPolicy Bypass -File "D:\Taadaa\Tiktok-video\run_tiktok_upload_avatar.ps1" `
    -Tik 3 `
    -AssignmentManifest "D:\CodexRuntime\tiktok-video\assignment-manifest-avatar-tik3.json" `
    -WorkerId "hermes-kibe-avatar" `
    -ForceAvatarMachineList "1,2,3...76" `
    -MaxParallel 40
  ```

## 2. Bẫy trôi nút Sửa hồ sơ sau Profile Grid scan baseline
- **Hiện tượng**: Sau bước `ACCOUNT_READY` quét cuộn lưới video (đếm baseline), Profile bị dừng ở lửng dưới trang. Nút Sửa hồ sơ (layout mới dạng icon bút chì cạnh username tại `bounds=[777..943, 510..594]`) bị trôi khỏi màn hình.
- **Hậu quả**: `_find_profile_edit_button` trả `None` -> Script kích hoạt fallback deep-link `snssdk1233://profile/edit` -> TikTok chặn popup anti-fraud: *"Hoạt động không có sẵn. Để tiếp tục tham gia vào các hoạt động, hãy chuyển sang tài khoản ban đầu mà bạn đã dùng trên thiết bị này."*
- **Fix chuẩn**:
  - Khi bắt đầu `_handle_ensure_avatar_impl`, luôn thực hiện 2 lần swipe cuộn về đỉnh Profile:
    `adb.shell(["input", "swipe", "540", "400", "540", "1500", "300"])`
  - Bổ sung filter loại bỏ nút bài đăng/bản nháp/thêm người để nhận diện chính xác icon bút chì cạnh username.

## 3. Photo Picker & Crop Screen layout mới (TikTok 46.x)
- **Nút Tiếp trên Photo Picker**: Nút Tiếp góc dưới phải có `resource_id="xip"` (`[780,1788][1044,1896]`). Cần thêm `xip` vào danh sách selector đợi nút Tiếp bên cạnh `o_9` và `wrj`.
- **Màn hình Cắt (Crop)**:
  - Checkbox "Đăng ảnh này lên Nhật ký" (`id/sca` tại `[48,1554][120,1626]` -> tap `(84, 1590)` để bỏ tick tránh đăng story).
  - Nút **"Lưu"** tại `[552,1728][1032,1860]` (tâm `(792, 1794)`) hoặc nút **"Lưu và đăng"** tại `[96,1698][984,1830]` (tâm `(540, 1764)`).

## 4. Hook `coordinate_fallback` trong `TikTokAdapter`
- **Nguyên nhân**: Khi tài khoản mới có onboarding card ("Hoàn tất hồ sơ", "Thêm ảnh", "Chia sẻ thói quen"), hàm `find_switcher_anchor` trong `automation-core` bị ambiguous và tìm gọi `adapter.coordinate_fallback("switcher")`. Nếu consumer adapter không implement hook này, runner văng lỗi `SWITCHER_ANCHOR_AMBIGUOUS`.
- **Fix chuẩn**:
  ```python
  def coordinate_fallback(self, action: Optional[str] = None) -> Optional[tuple[int, int]]:
      """Coordinate fallback for core account_switcher when anchor is ambiguous."""
      if action == "switcher":
          # TikTok 46.x profile header display name / username anchor
          return (540, 552)
      return None
  ```

## 5. PYTHONPATH Isolation cho Python venv
- Khi chạy script từ terminal MSYS/bash (như `reconcile_tiktok_accounts.py`), `PYTHONPATH` có thể kế thừa môi trường ngoài làm nạp nhầm package C-extension (ví dụ `PIL._imaging` từ hermes venv) gây `ImportError`.
- Sử dụng `env -u PYTHONPATH <python_path> <script_path> ...` để bảo đảm venv chạy hoàn toàn cô lập.
