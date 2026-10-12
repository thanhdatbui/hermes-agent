# Friends Feed Empty Recommendation Popup False-Positive Triage (2026-10-12)

## 1. Triệu chứng & Bối cảnh
- Khi chạy ca nuôi acc TikTok (`multi_machine_feed_session` / `feed_swipe_smoke.py`), hàng loạt máy (ví dụ Ca 3 Tối: M204, M212, M214, M244, M269, M277 trên Farm Admin và M72 trên Farm Kibe) bị dừng sớm với lỗi:
  ```text
  step: switch_friends_<N>_navigation_confirm_after_popup_dismiss
  expected: Friends feed
  detected: for-you
  status: failed
  reason: feed not confirmed
  ```
- Thử điều hướng lại tab Bạn bè (`Friends`) nhiều lần vẫn bị văng về tab "Đề xuất" (`for-you`) rồi kết thúc session với `fail`.

## 2. Truy vết Nguyên nhân gốc rễ (Root Cause)
1. **Giao diện tab Bạn bè khi chưa có bài đăng của bạn:**
   TikTok hiển thị thẻ gợi ý tìm kiếm bạn bè từ danh bạ với các cụm từ:
   - *"Hãy follow bạn bè để xem video của họ"*
   - *"Danh bạ"* / *"Tìm các liên hệ của bạn"*
   - *"Follow lại"* / *"Follow"*
   - Các nút tab trên đỉnh: *"Cộng đồng"*, *"Đà Nẵng"*, *"Bạn bè"* (đang chọn), *"Đã follow"*, *"Đề xuất"* (bounds `[853, 72][912, 246]`), icon Tìm kiếm (`[912, 75][1080, 243]`).

2. **Lỗ hổng nhận diện trong `detect_contact_follow_suggestion` (`automation-core`):**
   - Hàm `detect_contact_follow_suggestion` quét thấy từ khóa `"danh bạ"` và nút `"Follow lại"`, nên coi đây là popup gợi ý kết bạn.
   - Thiếu bộ lọc loại trừ màn hình Friends feed (trong khi trước đó đã có `profile_markers` để loại trừ màn hình trang cá nhân).

3. **Lỗ hổng chọn nút đóng fallback trong `_close_candidate`:**
   - Khi không tìm thấy nút đóng `"Không quan tâm"` hay icon close-X tường minh (`:id/e63`, `:id/c3t`), fallback `_close_candidate` quét các view clickable không có nhãn ở góc trên phải (`left >= 800`, `top <= 350`).
   - Container của tab **"Đề xuất"** (class `X.004T`, bounds `[853, 72][912, 246]`) có text rỗng trên node cha (text nằm ở TextView con), nên bị nhận diện nhầm thành nút đóng popup.

4. **Hậu quả điều hướng:**
   - Script gọi handler đóng popup `dismiss_not_interested_button` $\rightarrow$ tap trúng tọa độ `[882, 159]` của tab "Đề xuất".
   - TikTok lập tức chuyển sang For You feed.
   - Bộ kiểm tra sau đóng popup quan sát thấy `detected='for-you'`, lệch với `expected='Friends feed'` $\rightarrow$ kích hoạt cờ `feed not confirmed` và dừng phiên.

## 3. Quy chuẩn Khắc phục & Phòng vệ 2 Lớp (Defense in Depth)

### Lớp 1: Bổ sung Friends Feed Markers vào `detect_contact_follow_suggestion`
Trong `src/automation_core/tiktok/benign_popup.py`, bỏ qua ngay lập tức khi phát hiện các đặc trưng nội dung của tab Bạn bè:
```python
friends_feed_markers = (
    "hãy follow bạn bè để xem video của họ",
    "hÃ£y follow báº¡n bÃ¨",
    "kết nối với bạn bè để xem bài đăng",
    "káº¿t ná»‘i vá»›i báº¡n bÃ¨",
    "tìm các liên hệ của bạn",
    "tÃ¬m cÃ¡c liÃªn há»‡ cá»§a báº¡n",
    "kết nối với liên hệ trong danh bạ",
    "kết nối với bạn bè trên facebook",
)
if _has_contains(values, friends_feed_markers):
    logger.debug("detect_contact_follow_suggestion: skipping friends feed matching marker")
    return None
```

### Lớp 2: Thắt chặt điều kiện Dismiss Target của Contact Follow Suggestion
CẤM TUYỆT ĐỐI dùng view không nhãn (`unlabeled_candidates`) ở thanh tab trên đỉnh làm nút đóng:
```python
if dismiss_target is None:
    close_cand = _close_candidate(filtered_elements)
    if close_cand is not None and (close_cand.content_desc or close_cand.text).strip().casefold() in _ADD_PHONE_CLOSE_LABELS:
        dismiss_target = close_cand
```

### Lớp 3: Bổ sung xử lý Popup trong `_post_swipe_for_you_recovery`
Tại hàm phục hồi lệch feed `_post_swipe_for_you_recovery` (`feed_swipe_smoke.py`), nếu màn hình sau khi quay lại For You trúng popup cho phép đóng (ví dụ thẻ liên hệ trong feed), bắt buộc phải chạy qua `_maybe_dismiss_allowed_popup_after_swipe` thay vì lập tức báo fail.
