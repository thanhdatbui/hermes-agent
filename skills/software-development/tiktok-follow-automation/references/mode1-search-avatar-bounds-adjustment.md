# Mode 1 Search Result Avatar Bounds Adjustment

## Root Cause
Trên TikTok 46.x (Top & Users search results), kết quả tìm kiếm account card thường là ViewGroup dạng ngang trải dài toàn màn hình (ví dụ `RelativeLayout` bounds `[0, 615][1080, 837]`, width 1080px, height 222px, `w > h * 1.5`).
Khi card này không chứa node `ImageView` con có clickable riêng (hoặc `ImageView` không trùng bounds), `_exact_search_result_from_xml` trước đây trả về toàn bộ node ViewGroup `target_element`.
Khi đó, hàm `tap_center(adapter, node)` tính tâm `(x + w // 2, y + h // 2)` rơi vào `(540, 726)` (khoảng trắng giữa card / vùng text không clickable). Trên TikTok thực tế, chạm vào khoảng trắng giữa card không mở Profile người dùng.

## Solution Contract
1. Trong `_exact_search_result_from_xml(xml_text: str, uid: str)`:
   - Nếu tìm thấy 1 `avatar_target` (descendant clickable `ImageView` khớp bounds candidate): trả về `avatar_target`.
   - Nếu có nhiều `avatar_targets`: trả về `None` (fail closed).
   - Nếu không có `avatar_target` (`len(avatar_targets) == 0`):
     - Kiểm tra nếu `target_element != identity_element` và `w > h * 1.5` (card dạng ngang):
     - Điều chỉnh bounds về hình vuông avatar bên trái: `bounds = (x, y, min(w, h), h)` và `bounds_size = (min(w, h), h)`.
     - Với `(0, 615, 1080, 222)`, bounds trở thành `(0, 615, 222, 222)` -> `tap_center` sẽ chạm vào `(111, 726)` (avatar của tài khoản), mở Profile thành công.
     - Ngược lại, trả về nguyên bản `nodes[element_index[target_element]]`.

## Regression Test Matrix
- Horizontal card without ImageView (`id/v09` `[0, 615][1080, 837]`): bounds adjusted to `(0, 615, 222, 222)`.
- Horizontal card with clickable ImageView: returns exact ImageView node `(51, 399, 168, 168)`.
- Direct text node / identity element (`target_element == identity_element`): bounds remain untouched.
