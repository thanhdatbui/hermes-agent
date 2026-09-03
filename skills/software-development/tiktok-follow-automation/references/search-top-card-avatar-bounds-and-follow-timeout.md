# Search Top Card Avatar Bounds and Follow Timeout Fix (Case UI-40)

## Problem Description
Trong luồng Mode 1 search-follow (`mode1_search_follow.py`), sau khi gõ UID tìm kiếm:
1. TikTok 46.x hiển thị kết quả tài khoản trên tab Top dưới dạng card ngang `RelativeLayout` (ví dụ `id/v09` hoặc `id/uzz`, bounds `[0, 615][1080, 837]`, chiều rộng 1080px, chiều cao 222px).
2. Card này không chứa node `ImageView` riêng biệt trong cây XML (chỉ chứa các `TextView` cho username, display name và `Button` `id/tvn` cho nút Follow).
3. Logic cũ trong `_exact_search_result_from_xml` tìm kiếm `avatar_targets` bằng cách duyệt các `ImageView` con. Khi không tìm thấy `ImageView`, hàm trả về toàn bộ `target_element` với bounds `(0, 615, 1080, 222)`.
4. `tap_center` tính tọa độ trung tâm `(540, 726)` (trung tâm card theo chiều ngang). Trên TikTok 46.x, việc bấm vào vùng text/khoảng trống ở giữa card không kích hoạt sự kiện mở Profile.
5. Ứng dụng vẫn kẹt ở trang Kết quả tìm kiếm (Search Results). Khi hàm tiếp theo `_classify_exact_profile_action` kiểm tra UI dump, nó không thấy trang Profile của target mà thấy màn hình Search, trả về `identity_mismatch` và bỏ qua UID.
6. Quá trình tìm kiếm - không mở được profile - khôi phục feed lặp lại liên tục cho các UID tiếp theo cho đến khi chạm mốc timeout 1200s (`follow-timeout`), kích hoạt alert dừng phiên `[MÁY N] DỪNG PHIÊN • Script: tiktok-follow • Lý do: follow-timeout`.

## Root Cause
- Tọa độ tap vào card tài khoản ngang bị tính lệch vào vùng trống không nhận tương tác (Center X = 540) thay vì vùng Avatar bên trái của card.

## Solution & Implementation Contract
Trong `_exact_search_result_from_xml(xml_text: str, uid: str)`:
Khi `avatar_targets` trống (`len(avatar_targets) == 0`) và `target_element` là card nằm ngang (`w > h * 1.5`):
- Điều chỉnh bounds của target node về hình vuông avatar ở góc trái: `(x, y, min(w, h), h)`.
- Ví dụ: Bounds `(0, 615, 1080, 222)` được điều chỉnh thành `(0, 615, 222, 222)`.
- Khi đó `tap_center` sẽ bấm vào `(111, 726)` (tâm của ô avatar bên trái), đảm bảo 100% mở được Profile của target trên TikTok.

```python
target_node = nodes[element_index[target_element]]
bounds = target_node.get("bounds")
if target_element != identity_element and bounds and len(bounds) == 4:
    x, y, w, h = bounds
    if w > h * 1.5:
        avatar_dim = min(w, h)
        adjusted = dict(target_node)
        adjusted["bounds"] = (x, y, avatar_dim, h)
        adjusted["bounds_size"] = (avatar_dim, h)
        return adjusted
return target_node
```

## Regression Test Coverage
- Unit test `test_exact_search_result_horizontal_card_without_imageview_adjusts_bounds`: Xác nhận card ngang `[0, 615][1080, 837]` không có `ImageView` được điều chỉnh bounds thành `(0, 615, 222, 222)`.
- Unit test `test_nav_search_switches_to_users_tab_when_not_in_top_tab` & `test_reload_profile_switches_to_users_tab_if_needed`: Xác nhận tọa độ tap avatar `(111, 483)` cho card `[0, 372][1080, 594]`.
