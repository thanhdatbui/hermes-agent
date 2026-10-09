# Bẫy Switcher Anchor nhận nhầm Username ở thân Profile (y > generic_header_y)

## Triệu chứng & Nguyên nhân
Trên TikTok (như Máy 1), tại màn hình Profile root khi chưa cuộn (unscrolled layout):
- Node `@username` (ví dụ `@tranngan767`) nằm ở thân profile dưới avatar (`bounds=[400,594][679,639]`, `center_y = 616`).
- Node này có `clickable="true"` và màn hình có `"menu hồ sơ"` / `"profile menu"` (`has_profile_menu = True`).
- Trong hàm `find_switcher_anchor()` của `automation_core.tiktok.account_switcher`:
  Nhánh `username_candidates` cũ:
  ```python
  (
      node.center[1] <= header_y
      or (has_profile_menu and node.attributes.get("clickable", "false").casefold() == "true")
  )
  and node.text.strip().startswith("@")
  ```
  Nhánh `has_profile_menu and clickable` thiếu chặn trần `y <= generic_header_y` (320px). Do đó, `@tranngan767` ở `y=616` bị nhận diện sai thành switcher anchor!

## Hậu quả nghiêm trọng
1. Khi tap vào node `@username` ở thân profile, TikTok chỉ sao chép ID vào clipboard ("Đã sao chép ID TikTok"), hoàn toàn không mở sheet "Chuyển đổi tài khoản".
2. Vì `find_switcher_anchor` trả về `anchor is not None`, luồng `open_switcher()` bỏ qua bước `prepare_switcher_anchor()` (hàm swipe nhẹ 400px để kéo nick dính vào sticky header trên đỉnh). Hậu quả là toàn bộ flow đăng nhập/reconcile bị kẹt hoặc báo `SWITCHER_ANCHOR_AMBIGUOUS`.

## Quy tắc & Bản vá chuẩn (automation-core)
1. **Chặn trần cho username_candidates**: Mọi candidate bắt đầu bằng `@` để mở switcher ở header PHẢI thỏa mãn `node.center[1] <= generic_header_y`. Tuyệt đối không nhận bất kỳ node nào ở thân profile (`y > generic_header_y`).
2. **Loại trừ body username trong identity_candidates và preferred_candidates**:
   Thêm điều kiện `not (node.text.strip().startswith("@") and node.center[1] > generic_header_y)`.
3. Khi `find_switcher_anchor` trả về `None`, `open_switcher` sẽ gọi `prepare_switcher_anchor()` để vuốt màn hình hiển thị sticky header trên đỉnh (`y <= generic_header_y`), sau đó mới tìm lại anchor và mở switcher thành công.
