# TikTok Profile Video Pinning & Upload Reconciliation

## 1. Cơ chế Ghim (Pin) Video trên TikTok Profile qua ADB
- **Thao tác tối ưu:** Không cần mở player video rồi bấm menu 3 chấm `...`.
- **Thao tác đè cảm ứng (Long-press):**
  - Thực hiện lệnh: `adb -s <serial> shell input swipe <X> <Y> <X> <Y> 1000` trực tiếp tại tọa độ tâm của ô video (tile) trên Profile grid.
  - Sau ~1 giây, TikTok sẽ bật **Action Sheet** từ đáy màn hình.
  - Các tùy chọn trong Action Sheet:
    * `"Ghim lên đầu"` / `"Pin to top"` (nếu chưa ghim).
    * `"Bỏ ghim khỏi đầu"` / `"Unpin from top"` (nếu đã ghim).
    * `"Đặt ở chế độ riêng tư"` / `"Set to private"`.
    * `"Chia sẻ"` / `"Share"`.
  - Tap vào tọa độ của node `"Ghim lên đầu"` / `"Pin to top"` để ghim.
- **Giới hạn TikTok:** Mỗi tài khoản ghim tối đa 3 video.

## 2. Ảnh hưởng đối với quy trình đối soát & Upload
- **`_verify_profile_post_increment` (state_machine.py):**
  - Script đếm tổng số video tiles qua hàm `_count_profile_video_tiles_across_grid()` (`baseline` vs `current`).
  - Video được ghim vẫn là một video tile hợp lệ (có `tv_play_count`, `id/eti`, `id/cover`), chỉ mang thêm nhãn `"Đã ghim"` / `"Pinned"`.
  - Khi đăng video mới, tổng số tiles tăng từ $N \to N + 1$ $\implies$ điều kiện `current > baseline` thỏa mãn 100%.
  - Script **không phụ thuộc** vào việc video mới nhất phải nằm ở ô đầu tiên `[0, 0]`.
- **`VIDEO_PICK` (Upload flow):**
  - Chọn video từ thư viện máy (`Download` folder), không đụng vào lưới Profile.
  - Tại `state_machine.py:10061` (`_is_video_pick_profile_action_sheet`), hệ thống đã có sẵn handler nhận diện Action Sheet ghim video để tự bấm Back nếu vô tình chạm trúng khi bấm nút `+`.
- **Workbook & Tracker:**
  - Workbook ghi nhận theo số thứ tự file video nguồn (`context.video_number`).
  - Tracker (`tiktok_account_tracker.py`) đọc chỉ số `stats['videoCount']` từ JSON, không bị ảnh hưởng bởi thứ tự ghim.
