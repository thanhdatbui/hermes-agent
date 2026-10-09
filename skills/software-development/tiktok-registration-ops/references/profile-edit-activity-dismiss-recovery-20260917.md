# TikTok ProfileEditActivity Dismiss & Recovery (2026-09-17, Case 143, Máy 40)

## Hiện tượng
- Trong chuỗi reg hoặc account reconcile/logout, `go_to_profile(device_id)` (trong `social_reg_v1.py`) bị fail với:
  `RuntimeError: [02_profile] Khong vao duoc tab Ho so/Profile`
- Artifact XML cho thấy UI đang ở màn hình:
  `com.ss.android.ugc.trill/com.ss.android.ugc.profile.business.ur.ui.ProfileEditActivity` (màn hình "Sửa hồ sơ").

## Nguyên nhân
1. App TikTok còn lưu session sửa profile từ trước đó hoặc vô tình tap vào nút "Sửa hồ sơ".
2. Khi ở `ProfileEditActivity`, toàn bộ thanh bottom navigation bar (Home, Friends, Inbox, Profile) bị ẩn.
3. Các tọa độ fallback đáy màn hình (`(972, 1857)`) tap trúng vùng không có tác dụng điều hướng.
4. `dismiss_profile_overlays()` chỉ kiểm tra popup dialog hoặc màn hình đặt tên (`tv_content_name`), chưa xử lý Activity con `ProfileEditActivity`.

## Giải pháp (Commit `b3c3cce` trên `Tiktok_Reg`)
1. Bổ sung block kiểm tra trong `dismiss_profile_overlays(device_id)`:
```python
if "sua ho so" in flat and any(k in flat for k in ["quay lai man hinh truoc", "thay doi anh", "ten nguoi dung"]):
    log("   [profile] dismiss ProfileEditActivity (quay lại Profile chính)")
    if not find_text_tap(device_id, "Quay lại màn hình trước", "Quay lai man hinh truoc", wait=D_SHORT):
        keyevent(device_id, 4, wait=D_SHORT)
    time.sleep(D_SHORT)
    continue
```
2. Ưu tiên tìm text content-desc `"Quay lại màn hình trước"` của nút back top-left (`bounds="[24,12][144,144]"`). Nếu không tap được thì fallback sang `keyevent 4` (KEYCODE_BACK).
3. Đã verify qua unit test `tests/test_profile_edit_dismiss.py` (3 test cases pass 100%).
