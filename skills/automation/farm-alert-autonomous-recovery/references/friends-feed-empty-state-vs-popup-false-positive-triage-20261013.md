# Friends Feed Empty State vs Contact Follow Suggestion False-Positive Triage (2026-10-13)

## 1. Hiện tượng & Triệu chứng
- Trong các ca nuôi lướt Feed (Ca 1/2/3/4), hàng loạt máy cùng thất bại với lỗi `feed not confirmed` tại bước chuyển sang tab Bạn bè (`Friends`):
  `step: switch_friends_X_navigation_confirm_after_popup_dismiss expected: Friends feed detected: for-you reason: feed not confirmed`
- Triệu chứng lặp lại trên nhiều máy (ví dụ Ca 3: M204, M212, M214, M244, M269, M277...).
- Máy sau đó retry chuyển tab nhưng vẫn bị giật ngược về tab Đề xuất (`For You`), dẫn đến fail phiên và chuyển trạng thái `failed` / `manual-needed`.

## 2. Cơ chế lỗi & Phân tích hiện trường (Root Cause)
1. **Empty State của Tab Bạn bè:**
   - Khi tài khoản chưa kết nối bạn bè hoặc bạn bè chưa đăng video mới, TikTok hiển thị giao diện mặc định gợi ý kết nối trong feed tab:
     * Tiêu đề: *"Hãy follow bạn bè để xem video của họ"*
     * Danh mục: *"Danh bạ"*, *"Tìm các liên hệ của bạn"*
     * Nút danh thiếp: *"Follow bạn"*, *"Follow lại"*, *"Mời Bạn bè"*
2. **False-Positive Trigger trong Popup Detector:**
   - Hàm `detect_contact_follow_suggestion` trong `automation_core/tiktok/benign_popup.py` quét toàn bộ text XML và tìm thấy:
     * `contact_marker`: từ các cụm *"danh bạ"*, *"follow bạn bè"*, *"tìm các liên hệ của bạn"*
     * `follow_marker`: từ nút *"follow lại"*
3. **Tai hại từ Fallback `_close_candidate`:**
   - Do đây là màn hình tab feed thông thường (không phải modal dialog), màn hình KHÔNG có nút đóng "Không quan tâm" hay icon đóng `:id/e63`.
   - Hàm `_close_candidate` quét các view ở góc trên bên phải (`left >= 800, top <= 350`) và bắt trúng container layout `X.004T` của tab **"Đề xuất" (For You)** (`bounds=[853, 72][912, 246]`).
   - Kết quả: `detect_contact_follow_suggestion` kết luận container tab "Đề xuất" chính là nút đóng X của popup!
4. **Hậu quả điều hướng:**
   - `classify_tiktok_screen` nhận diện màn hình là `manual-needed:popup` (`known contact_follow_suggestion popup detected`).
   - Handler `_maybe_dismiss_navigation_confirm_popup` thực hiện tap vào vị trí nút đóng $\rightarrow$ tap trúng tab "Đề xuất".
   - Feed ngay lập tức bị chuyển về "Đề xuất" trong khi runner đang chờ xác nhận tab Bạn bè $\rightarrow$ đánh rớt với `reason: feed not confirmed`.

## 3. Bản vá chuẩn hóa (Patch Pattern)
- Trong `automation_core/tiktok/benign_popup.py`, bổ sung guard loại trừ `friends_feed_markers` ngay đầu hàm `detect_contact_follow_suggestion` (tương tự như guard loại trừ `profile_markers` cho màn hình cá nhân):
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
- Thêm unit test xác minh loại trừ Friends feed trong `tests/test_tiktok_benign_popup.py`.
- Khi kiểm tra XML hiện trường, xác nhận `classify_tiktok_screen` trả về đúng `screen='friends', manual_needed=False`.
