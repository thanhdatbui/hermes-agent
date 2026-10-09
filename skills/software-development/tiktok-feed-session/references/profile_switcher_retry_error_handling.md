# Profile Switcher Retry & "Thử lại / Đã xảy ra lỗi" Recovery

## Bối cảnh
Khi switch profile trong TikTok (`verify_and_switch_profile` trong `feed_swipe_smoke.py`), sau khi tap tài khoản trong account switcher sheet, TikTok đôi khi không chuyển ngay sang profile mới hoặc hiển thị dialog lỗi hệ thống / mạng tạm thời:
- Resource ID: `com.ss.android.ugc.trill:id/dcj`
- Text nhận diện: "Thử lại", "Đã xảy ra lỗi"
- Hoặc XML profile vẫn còn cache thông tin tài khoản trước đó trong vài giây.

## Quy trình xử lý tự động trong code
1. **Kiểm tra trạng thái**: `not verified and selected_account_by_exact_switcher`
2. **Detect dialog lỗi**:
   - Quét `recaptured_xml` tìm `com.ss.android.ugc.trill:id/dcj` hoặc text `thử lại` / `đã xảy ra lỗi`.
   - Nếu có: dispatch tap nút Thử lại tại tọa độ `(540, 1436)`, chờ 3.0s.
   - Nếu không có dialog nhưng chưa verified (do XML cache trễ): chờ 2.5s.
3. **Re-capture identity**:
   - Gọi `_read_profile_identity_with_add_phone_guard` để dump XML mới và parse lại username / display_name.
   - Đánh giá lại điều kiện `verified`.
