# Case 165: Empty Friends/Following Feed Fallback & Direct Focused Verification Pattern

## 1. Problem Signature
- Thống kê tỷ lệ like ở tab Bạn bè (Friends) và Đang Follow (Following) thấp bất thường (~11-18%), dù cấu hình đặt 70%.
- Các tài khoản mới hoặc acc chưa follow ai khi chuyển sang tab Bạn bè/Following sẽ không có video thật mà chỉ hiện màn hình gợi ý rỗng (*"Hãy follow bạn bè để xem video của họ"*, *"Nhật ký"*, *"Tác giả nổi bật"*...).
- Runner cũ vẫn swipe tiếp 8-11 nhịp trên màn hình gợi ý liên hệ làm phình to mẫu số `feed_counts` mà `like_counts = 0`.
- Hàm `_maybe_like_video` bị chặn cứng bởi `clickable == "true"`, bỏ sót các container nút Like bọc ngoài hoặc nút hiển thị text count `lượt thích` / `likes`.

## 2. Core Solution
1. **Tăng tỷ lệ like sau dice:** Nâng mặc định `following: 50%`, `friends: 80%`.
2. **Mở rộng selector Like:** Bỏ ràng buộc cứng `clickable`, thêm regex bắt text `lượt thích` / `likes`, thêm log chi tiết `already_liked` / `button_not_found`.
3. **Bổ sung marker rỗng:** Thêm `"Hãy follow bạn bè"` vào `_FRIENDS_FEED_CONTENT_TERMS` (cùng `"Nhật ký"`, `"Tác giả nổi bật"`).
4. **Empty Feed Early Fallback:** Khi ở tab Friends/Following phát hiện nội dung gợi ý rỗng (không có video), runner tự động bấm chuyển quay về tab Đề xuất (`FEED_TYPE_FOR_YOU`) ngay nhịp đó để tiếp tục xem và thả tim video thật.

## 3. Critical Workflow Pitfall: Direct Focused Probe Verification
- **Anti-Pattern (Xà quằn / Blind runner batch):**
  - Chạy cả session runner dài hoặc `--recovery-test-swipes 4` để test 1 hàm đơn lẻ.
  - Biến đếm `videos_until_tab_decision = random.randint(3, 8)` khiến máy lướt 4 video ở For-You mà chưa hề nhảy vào tab Bạn bè/Following -> canary inconclusive, tốn thời gian vô ích và gây ức chế cho operator.
- **Correct Pattern (Test trực diện logic vừa sửa):**
  - Bỏ qua toàn bộ flow lướt feed khởi đầu.
  - Dùng ADB/ATX tap thẳng vào target tab (vd tab Bạn bè/Đã follow).
  - Dump UI XML kiểm tra đúng marker rỗng (`['Nhật ký']`, `['Hãy follow bạn bè']`).
  - Kích hoạt thẳng hành động fallback quay về For-You và đối soát XML `selected="true"` ngay lập tức.
  - Chụp ảnh screencap nghiệm thu trong < 1 phút.
