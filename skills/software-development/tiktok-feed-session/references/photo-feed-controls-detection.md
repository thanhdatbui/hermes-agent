# Nhận diện Hợp lệ Post dạng Photo (Ảnh) trên TikTok Feed

## 1. Bối cảnh & Hiện tượng
Khi chạy nuôi tài khoản hoặc smoke test feed session trên các máy farm (đặc biệt Máy 26 và các máy tương tự), TikTok phân phối cả post dạng **Photo (slideshow ảnh / album ảnh)** xen kẽ video.
Nếu classifier chỉ kiểm tra các từ khóa video truyền thống ("thích video", "bình luận"), post dạng Photo sẽ bị coi là màn hình lạ/không xác định (`unknown`), kích hoạt vòng lặp recovery không đáng có hoặc dừng session sai.

## 2. Đặc điểm UI của Post dạng Photo
- **Comment button:** Thay vì "Bình luận", ô bình luận hoặc icon thường mang placeholder `"Bóc tem"` hoặc chuỗi mã hóa `"bÃ³c tem"`.
- **Follow / Repost button:** Xuất hiện nút `"Đăng lại cho follower"` hoặc `"repost"`.
- **Photo marker:** Có nhãn `"Ảnh"` hoặc `"photo"` hoặc `"đăng lại"`.
- **Bookmark / Lưu:** Có các nút bookmark với text/content-desc `"bookmark"`, `"lưu"`, `"yêu thích"`.

## 3. Quy chuẩn Code trong Python Runner

### File 1: `core/classifier.py` (`_has_feed_detail_controls`)
Bắt buộc mở rộng 7 markers và yêu cầu `sum(...) >= 3`:
```python
def _has_feed_detail_controls(elements: list[UIElement]) -> bool:
    values = [
        " ".join(
            value
            for value in (element.text, element.content_desc, element.resource_id)
            if value
        ).strip().lower()
        for element in elements
    ]
    values = [value for value in values if value]
    like_marker = any(
        "thích video" in value
        or "thÃ­ch video" in value
        or value == "thích"
        or value == "thÃ­ch"
        for value in values
    )
    comment_marker = any(
        "bình luận" in value
        or "bÃ¬nh luáº­n" in value
        or "bóc tem" in value
        or "bÃ³c tem" in value
        for value in values
    )
    share_marker = any("share" in value or "chia sẻ" in value or "chia sáº»" in value for value in values)
    follow_marker = any(
        value.startswith("follow ")
        or "follow " in value
        or "đăng lại cho follower" in value
        or "repost" in value
        for value in values
    )
    avatar_marker = any("user_avatar" in value or "hồ sơ " in value or "há»“ sÆ¡" in value for value in values)
    photo_marker = any(value == "ảnh" or value == "photo" or "đăng lại" in value for value in values)
    bookmark_marker = any("bookmark" in value or "lưu" in value or "yêu thích" in value for value in values)

    return sum(
        bool(marker)
        for marker in (
            like_marker,
            comment_marker,
            share_marker,
            follow_marker,
            avatar_marker,
            photo_marker,
            bookmark_marker,
        )
    ) >= 3
```

### File 2: `flows/feed_swipe_smoke.py` (`_is_feed_confirmed`)
Bổ sung kiểm tra an toàn đa tầng cho `attempt`:
```python
    if (
        attempt.get("for_you_selected")
        or attempt.get("home_selected")
        or attempt.get("detected_screen") in FEED_SCREENS
        or attempt.get("screenshot_marker") in FEED_SCREENS
    ):
        return True
```
Tránh phụ thuộc duy nhất vào parser heuristic khi các cờ định vị feed (`for_you_selected`, `home_selected`) hoặc kết quả screen detector đã ghi nhận rõ màn feed.
