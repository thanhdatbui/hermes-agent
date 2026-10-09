# Feed Like & Follow Button Selector Standards (TikTok App Android)

## 1. Bản chất thay đổi UI của TikTok
- Trước đây nút like chỉ mang `content-desc="Thích"`.
- Hiện tại TikTok Android cập nhật động `content-desc` kèm số liệu engagement thời gian thực:
  - Ví dụ tiếng Việt: `"Thích video. 41,3K lượt thích"`, `"Thích video. 2.462 lượt thích"`.
  - Ví dụ tiếng Anh: `"Like video. 1.2M likes"`, `"Like video. 500 likes"`.
- Nút đã thích:
  - `"Đã thích video. 41,3K lượt thích"`, `"Bỏ thích"`, `"Liked video"`.

## 2. Cạm bẫy Selector trong Code (`find_by_fields`)
- `find_by_fields(root, content_desc="Thích")` dùng phép so sánh `==`.
- Kết quả: Suốt thời gian dài, 100% video đều không tìm thấy nút like, farm lướt 556 video với **0 like (zombie feed)** làm điểm Trust Score của tài khoản = 0, dẫn đến việc bị TikTok shadow-ban nhả follow hàng loạt.

## 3. Quy chuẩn Match Selector cho Feed Interaction
```python
# Nút Thích Video:
for element in iter_elements(root):
    desc = (element.content_desc or "").strip().lower()
    if (
        desc.startswith("đã thích video")
        or desc.startswith("bỏ thích")
        or desc.startswith("liked video")
    ):
        return False # Đã like rồi, không bấm nữa

    if element.center and element.clickable:
        if (
            desc.startswith("thích video")
            or desc == "thích"
            or desc.startswith("like video")
            or desc == "like"
            or "like_icon" in str(element.resource_id or "").lower()
        ):
            like_node = element
```

```python
# Nút Follow Video:
for element in iter_elements(root):
    if not element.center or element.center[1] < 350:
        continue # Lọc bỏ top navigation tab (Following / Bạn bè ở đỉnh màn hình)
    desc = (element.content_desc or "").strip()
    if element.clickable and (
        desc.startswith("Following") or desc == "Đang follow" or desc == "Đã follow" or desc == "Bạn bè"
    ):
        return False # Đã follow rồi

    if not follow_node and element.clickable:
        if desc.startswith("Follow ") or desc == "Follow" or desc.startswith("Theo dõi"):
            follow_node = element
```
- Áp dụng chuẩn xác trên cả 3 tab: Đề xuất (For You), Đang theo dõi (Following) và Bạn bè (Friends).
