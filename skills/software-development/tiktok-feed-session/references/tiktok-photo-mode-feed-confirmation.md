# TikTok Photo-Mode Feed Confirmation & Classifier Recovery

## 1. Hiện tượng & Triệu chứng Hiện trường
- **Alert**: `[FARM ALERT: MÁY N] screen capture invalid; feed not confirmed`.
- **Màn hình thực tế**: Điện thoại đang ở tab **"Đề xuất" (For You)** hoặc **"Bạn bè"**, hoàn toàn là màn hình feed hợp lệ, nhưng bài đăng hiển thị là dạng **Photo Mode (bài đăng nhiều Ảnh / Album ảnh)** thay vì video thông thường.
- **Đặc điểm UI dị biệt của bài đăng Photo Mode**:
  + **Nút Bình luận**: Hiển thị gợi ý `"Bóc tem"` (thay vì chữ `"Bình luận"` hoặc số lượng bình luận) khi bài chưa có ai bình luận.
  + **Nhãn định dạng**: Icon máy ảnh kèm chữ `"Ảnh"`.
  + **Nút Đăng lại / Repost**: `"Đăng lại cho follower"`.
  + **Nút Bookmark**: Icon dấu trang lưu trữ bài viết (`"Lưu"`, `"Bookmark"`, `"Yêu thích"`).
  + **Nút Follow**: Thường bị ẩn hoặc thay thế bởi ngữ cảnh quan hệ bạn bè/repost.

## 2. Phân tích Nguyên nhân Cốt lõi (Root Cause)
1. **Thiếu Selector trong Feed Controls Classifier (`core/classifier.py`)**:
   - Hàm `_has_feed_detail_controls(elements)` dùng để nhận diện màn hình feed khi top-tabs không có cờ `selected="true"` rõ ràng trong dump XML.
   - Hàm này yêu cầu tối thiểu 3 marker hợp lệ (`sum(...) >= 3`) trong tập: `like_marker`, `comment_marker`, `share_marker`, `follow_marker`, `avatar_marker`.
   - Với bài đăng Photo Mode có placeholder `"Bóc tem"` và không có nút follow truyền thống:
     * `comment_marker` miss vì chỉ match `"bình luận"`.
     * `follow_marker` miss vì chỉ match `"follow "`.
     * Thiếu hoàn toàn nhận diện nhãn `"Ảnh"` và nút `"Bookmark"`.
   - Hệ quả: Chỉ có `like_marker` và có thể `share_marker` khớp (tổng = 2 < 3) $\rightarrow$ `_has_feed_detail_controls` trả về `False`.

2. **Cơ chế Fail-Closed của `_is_feed_confirmed` (`flows/feed_swipe_smoke.py`)**:
   - Khi screencap gặp độ trễ hoặc XML dump trả về lỗi suy giảm trạng thái (degraded idle error), script kiểm tra `_is_feed_confirmed(attempt)`.
   - Khi classifier không gán được `detected_screen in {"home", "for-you", "sponsored"}` và screenshot top-tab không vượt ngưỡng confidence, hàm kết luận màn hình không phải feed.
   - Script văng lỗi `SCREEN_CAPTURE_INVALID_REASON = "screen capture invalid; feed not confirmed"` và kích hoạt dừng phiên.

## 3. Quy chuẩn Sửa Code (Standard Patch Pattern)

### A. Tại `python_runner/core/classifier.py` (`_has_feed_detail_controls`):
Bổ sung các markers của Photo Mode và mở rộng tập nhận diện:
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
        for marker in (like_marker, comment_marker, share_marker, follow_marker, avatar_marker, photo_marker, bookmark_marker)
    ) >= 3
```

### B. Tại `python_runner/flows/feed_swipe_smoke.py` (`_is_feed_confirmed`):
Đảm bảo `_is_feed_confirmed` xác thực feed khi có cờ `home_selected` hoặc `for_you_selected` hoặc kết quả classifier đã nhận diện được feed controls.

## 4. Kiểm chứng Canary B4
Sau khi patch, bắt buộc kiểm tra biên dịch cú pháp và kích hoạt Canary B4 trên đúng máy gặp sự cố:
```powershell
powershell.exe -ExecutionPolicy Bypass -File "D:\Taadaa\tiktok-luot nuoi acc\scripts\run-feed-session.ps1" -Machines <N> -Row 1 -RecoveryTestSwipes 2 -SkipAccountWorkbookSync -Run
```
