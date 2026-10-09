# Dismiss ProfileEditActivity ("Sửa hồ sơ") in TikTok Reg

## Bối cảnh
Khi tự động hóa đăng ký TikTok trên farm Samsung Galaxy, sau khi tạo tài khoản hoặc vào tab Profile, TikTok có thể tự động mở hoặc bị kẹt tại màn hình `ProfileEditActivity` ("Sửa hồ sơ").
Khi màn hình này hiển thị, hàm `dismiss_profile_overlays(device_id)` bị chặn không thể mở account switcher hoặc nhận diện tab Hồ sơ chính, dẫn đến lỗi:
`RuntimeError: [02_profile] Khong vao duoc tab Ho so/Profile`

## Dấu hiệu nhận diện trong UI XML
- XML chứa text / flat: `"sua ho so"`
- Kèm theo một trong các markers:
  - `"quay lai man hinh truoc"` (nút back của TikTok `ProfileEditActivity`, thường là ImageView có content-desc)
  - `"thay doi anh"`
  - `"ten nguoi dung"`

## Cách xử lý chuẩn trong `dismiss_profile_overlays(device_id)`
```python
if "sua ho so" in flat and any(k in flat for k in ["quay lai man hinh truoc", "thay doi anh", "ten nguoi dung"]):
    log("   [profile] dismiss ProfileEditActivity (quay lại Profile chính)")
    if not find_text_tap(device_id, "Quay lại màn hình trước", "Quay lai man hinh truoc", wait=D_SHORT):
        keyevent(device_id, 4, wait=D_SHORT)
    time.sleep(D_SHORT)
    continue
```

## Unit Test Contract
Khi viết test cho flow này (ví dụ `tests/test_profile_edit_dismiss.py`):
1. Mock `get_ui_xml` trả về XML chứa "Sửa hồ sơ" và "Quay lại màn hình trước", tiếp theo là clean profile XML.
2. Kiểm tra `find_text_tap` được gọi với ("Quay lại màn hình trước", "Quay lai man hinh truoc").
3. Khi `find_text_tap` trả về False, kiểm tra fallback gọi `keyevent(device_id, 4, wait=D_SHORT)`.
4. Khi không phải màn hình sửa hồ sơ, đảm bảo không tap back.
