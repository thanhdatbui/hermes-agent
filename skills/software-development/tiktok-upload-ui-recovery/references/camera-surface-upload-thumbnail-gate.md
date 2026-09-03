# Camera Surface Upload Thumbnail Visual Gate & Low-Light Rejection (2026-08-31)

## Bối cảnh & Hiện tượng (Incident Máy 38 - florencen2026)
- **Script**: `tiktok-video` (Tiktok-video repo, `scripts/tiktok_workflow/state_machine.py`)
- **Lỗi**: `upload_subprocess_nonzero` / `[VIDEO_PICK_CREATE_ENTRY_UNCONFIRMED] Picker was not verified after the bounded create-entry recovery`
- **Run Directory**: `D:\CodexRuntime\tiktok-video\runs\run_<serial>_<timestamp>\` (chứa `execution.log`, `checkpoint.json`, `report.json`, và các artifact `.png` như `video-pick-camera-surface.png`, `video-pick-create-entry-before.png`)

## Root Cause
1. Sau khi ấn nút `+` (Create), TikTok trên một số thiết bị mở giao diện Camera (`_is_camera_surface_xml` = True) thay vì mở thẳng gallery picker.
2. Helper `_tap_visual_camera_upload_entry` capture screenshot `video-pick-camera-surface.png` và crop vùng ô thumbnail Tải lên (`left=0.81w, top=0.77h, right=0.94w, bottom=0.87h`).
3. Gate tính tỷ lệ pixel sáng:
   ```python
   non_dark = sum(1 for red, green, blue in pixels if max(red, green, blue) > 35) / len(pixels)
   if non_dark < 0.45:
       logger.warning("Camera upload thumbnail visual gate rejected screenshot")
       return False
   ```
4. Khi camera của máy bị che / đặt trong hộp / môi trường tối, `non_dark` đo được chỉ đạt ~`0.3007` (< 0.45) nên visual gate reject → `_recover_video_pick_create_entry` fail → kích hoạt ladder B3 soft reboot → timeout proxy watcher → dừng phiên `MANUAL_REVIEW`.

## Hướng xử lý khi được user hướng dẫn
- Điều tra `execution.log` và trích xuất giá trị `non_dark` từ ảnh artifact `video-pick-camera-surface.png`.
- Tùy chỉnh threshold `non_dark` hoặc bổ sung semantic/coordinate tap an toàn cho nút Tải lên (Upload) trên giao diện Camera khi đã xác nhận `_is_camera_surface_xml`.
- Tuân thủ nghiêm ngặt STOP GATE: chụp screencap gửi user qua `MEDIA:<path>` dòng riêng, KHÔNG tự ý sửa code khi chưa có chỉ đạo.
