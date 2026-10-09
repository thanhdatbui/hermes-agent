# Case 103: TikTok 47.x Avatar Edit - Bẫy Story "Tạo một Nhật ký" & Lỗi Trôi Header Do Cuộn Grid Video

## Hiện tượng & Mã lỗi
Khi chạy upload avatar (`run_tiktok_upload_avatar.ps1 -Tik N -ForceAvatarMachineList "M"` hoặc mode `-AvatarOnly`):
- Runner bị lỗi:
  ```
  [PROFILE_EDIT] Matched layout detector right_pencil_button at bounds=[931,499][1080,636]
  ...
  [ENSURE_AVATAR] Các nhánh profile không mở; thử fallback deep-link cuối
  [ERROR] [AVATAR_EDIT_OPEN_FAILED] ENSURE_AVATAR: Màn Sửa hồ sơ không mở
  ```
- Hoặc trước đó:
  ```
  [AVATAR_WORKFLOW_FAILED] ENSURE_AVATAR: Avatar workflow failed: PROFILE_ROOT_NOT_CONFIRMED: Profile root was not confirmed
  ```

## Phân tích nguyên nhân gốc rễ (Root Cause)

1. **Bẫy layout "right_pencil_button" match nhầm nút Story:**
   - Trong `scripts/tiktok_workflow/state_machine.py`, hàm `_find_profile_edit_button` từng có layout detector:
     `right_pencil_button = (750 <= left <= 950 and 450 <= top <= 650 and 80 <= right - left <= 220 and 60 <= bottom - top <= 160)`
   - Trên tài khoản TikTok mới (như máy 34, account `lyvy981`), nút bút chì nằm ở **GÓC TRÊN BÊN TRÁI** (`bounds=[24,96][126,204]`, center `(75, 150)`).
   - Ở góc dưới bên phải avatar, TikTok đặt một nút dấu cộng nhỏ:
     `text='' cd='Tạo một Nhật ký' bounds=[931,499][1080,636]`
   - Do tọa độ `931` nằm trong `[750, 950]` và `499` nằm trong `[450, 650]`, detector này đã match nhầm nút "Tạo một Nhật ký", bấm vào làm mở camera Story (Hiển thị với follower trong 24 giờ / "Bạn có chuyện gì?"). Màn "Sửa hồ sơ" không bao giờ mở.

2. **Lỗi trôi Header do cuộn Profile Grid ở `ACCOUNT_READY`:**
   - Ở phase `ACCOUNT_READY`, hệ thống chạy `scroll_profile_grid` cuộn xuống 3 viewports để đếm baseline video tiles.
   - Hàm `_restore_profile_grid_top` trong `adapter.py` bị lỗi `Không tìm thấy scroll container khi restore; dừng ở viewport hiện tại` nên không kéo lại màn hình về đỉnh.
   - Hậu quả: Profile bị kẹt ở trạng thái scrolled down, phần Header chứa Avatar và Bút chì bị trôi ra khỏi màn hình (off-screen).
   - Khi đó `_looks_like_profile_root` không nhận diện được do không thấy "Sửa hồ sơ", dẫn đến vòng lặp bấm Back / gọi `bring_to_foreground` văng về Feed video và ném lỗi `PROFILE_ROOT_NOT_CONFIRMED`.

## Quy tắc & Bản vá chuẩn hóa

1. **Ưu tiên gọi `_find_new_profile_pencil` khi không có nút chữ:**
   - Trong `_find_profile_edit_button`, ngay sau khi quét text `Sửa hồ sơ` / `Edit profile`:
     ```python
     pencil = StateMachine._find_new_profile_pencil(xml_text)
     if pencil:
         logger.info("[PROFILE_EDIT] Matched top-left pencil: %s", pencil)
         return {"center": pencil}
     ```
   - Điểm tap `(75, 150)` lập tức mở chuẩn xác màn hình Sửa hồ sơ (`id=com.ss.android.ugc.trill:id/psy`) và nút `Thay đổi ảnh` (`id=com.ss.android.ugc.trill:id/yxg`).

2. **Khử bẫy Story:**
   - Tuyệt đối loại trừ các node có `content-desc` hoặc `text` chứa `"nhật ký"` / `"story"` trong mọi layout detector avatar / profile edit.

3. **Nhận diện Profile Root an toàn khi scrolled (chống False Positive):**
   - Trong `_looks_like_profile_root`, kiểm tra thêm trạng thái bottom-nav tab kèm resource-id chính xác:
     `'selected="true"' in lowered and 'content-desc="hồ sơ"' in lowered and 'id/oms' in lowered`
     Bắt buộc có `id/oms` (`com.ss.android.ugc.trill:id/oms`) để tránh false positive trên các màn hình khác chứa từ "hồ sơ".

4. **Chặn False Feed Foregrounding qua `bring_to_foreground`:**
   - Khi TikTok đã ở foreground (`_package_is_foreground(package) is True`), việc gọi `adapter.bring_to_foreground(package)` sẽ kích hoạt lệnh `am start -n com.ss.android.ugc.trill/.MainActivity`, dẫn đến việc Android khởi chạy qua `SplashActivity` và đẩy TikTok từ màn Profile về lại màn Feed video (Trang chủ).
   - Bản vá bắt buộc: Chỉ gọi `bring_to_foreground` khi package chưa thực sự ở foreground:
     ```python
     if not adapter._package_is_foreground(package) and adapter.bring_to_foreground(package):
         time.sleep(2)
         current_xml = adapter.dump_ui()
     ```

5. **Telemetry Observability cho nút Bút chì mới:**
   - Đánh dấu log chuẩn telemetry `[PROFILE_EDIT] [TELEMETRY] matched_control=top_left_pencil position=%s` để phục vụ audit tỷ lệ fallback và giám sát drift giao diện TikTok.
