# Nhận diện & Xác thực Bài đăng Dạng Ảnh (Photo Mode) trên TikTok Feed

## 1. Hiện tượng & Triệu chứng Alert
- **Alert:** `🚨 [FARM ALERT: MÁY N] DỪNG PHIÊN`
- **Triệu chứng:** `screen capture invalid; feed not confirmed`
- **Hiện trường:** Điện thoại đang ở tab "Đề xuất" (For You) hoặc "Trang chủ", nhưng bài đăng hiện tại là bài đăng dạng Ảnh (Photo mode) thay vì video dọc truyền thống.

## 2. Đặc điểm UI của Photo Mode Post
1. **Nút Bình luận:** Không có text số lượt bình luận hay chữ "Bình luận", thay vào đó hiển thị placeholder text `"Bóc tem"` (khi chưa có comment) hoặc icon chat đặc thù.
2. **Nút Repost:** Hiển thị nhãn `"Đăng lại cho follower"` hoặc `"Repost"`.
3. **Chế độ nội dung:** Có icon camera hoặc nhãn chữ `"Ảnh"` (hoặc `"Photo"`).
4. **Nút Lưu / Yêu thích:** Hiển thị icon bookmark kèm số lượt lưu (`"Bookmark"`, `"Lưu"`).

## 3. Nguyên nhân Gốc rễ (Root Cause)
1. **`core/classifier.py` (`_has_feed_detail_controls`):**
   - Hàm này yêu cầu tối thiểu 3 trong các nhóm marker: `(like_marker, comment_marker, share_marker, follow_marker, avatar_marker)`.
   - Trên photo post, text bình luận đổi thành `"Bóc tem"`, nút follow đổi thành `"Đăng lại cho follower"`, avatar/follow không khớp chuẩn cũ $\rightarrow$ tổng marker $< 3 \rightarrow$ phân loại UI không nhận ra feed (`screen="unknown"`).
2. **`flows/feed_swipe_smoke.py` (`_is_feed_confirmed`):**
   - Khi screencap bị lag hoặc XML dump trả về fallback, hàm kiểm tra `_is_feed_confirmed` không tìm thấy `detected in expected_feed_screens`.
   - Dẫn đến việc script fail-closed: `SCREEN_CAPTURE_INVALID_REASON = "screen capture invalid; feed not confirmed"`.

## 4. Giải pháp Chuẩn Hóa
1. **Mở rộng `_has_feed_detail_controls` trong `python_runner/core/classifier.py`:**
   ```python
   comment_marker = any(
       "bình luận" in value or "bÃ¬nh luáº­n" in value or "bóc tem" in value or "bÃ³c tem" in value
       for value in values
   )
   follow_marker = any(
       value.startswith("follow ") or "follow " in value or "đăng lại cho follower" in value or "repost" in value
       for value in values
   )
   photo_marker = any(value == "ảnh" or value == "photo" or "đăng lại" in value for value in values)
   bookmark_marker = any("bookmark" in value or "lưu" in value or "yêu thích" in value for value in values)

   return sum(
       bool(marker)
       for marker in (like_marker, comment_marker, share_marker, follow_marker, avatar_marker, photo_marker, bookmark_marker)
   ) >= 3
   ```
2. **Tăng cường `_is_feed_confirmed` trong `python_runner/flows/feed_swipe_smoke.py`:**
   - Xác nhận feed ngay nếu `detected_screen`, `screenshot_marker`, `for_you_selected`, hoặc `home_selected` nằm trong `FEED_SCREENS`.

## 5. Lệnh Canary Kiểm Chứng (B4)
```powershell
powershell.exe -ExecutionPolicy Bypass -File "D:\Taadaa\tiktok-luot nuoi acc\scripts\run-feed-session.ps1" -Machines <N> -Row 1 -RecoveryTestSwipes 2 -SkipAccountWorkbookSync -Run
```
Kỳ vọng: `final_status: success`, hoàn thành đủ số lượt swipe (2/2), `capture invalid: 0`.
