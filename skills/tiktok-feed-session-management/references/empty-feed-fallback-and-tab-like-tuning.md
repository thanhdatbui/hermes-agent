# Empty Feed Recovery & Tab-Like Tuning in TikTok Feed Session

## 1. Hiện Tượng & Nguyên Nhân
- **Triệu chứng:** Tỉ lệ like tab Bạn bè (Friends) và Đang Follow (Following) thấp bất thường (~6% - 18%) dù cấu hình tỷ lệ like cao (Following: 30-50%, Friends: 70-80%).
- **Nguyên nhân gốc rễ:**
  1. Các tài khoản mới hoặc tài khoản chưa follow/chưa kết bạn với ai khi chuyển sang tab Bạn bè hoặc Following sẽ **không có video player**.
  2. TikTok hiển thị giao diện danh thiếp gợi ý: *"Hãy follow bạn bè để xem video của họ"*, *"Tác giả nổi bật"*, danh bạ tìm bạn bè.
  3. Runner cũ không phát hiện màn hình rỗng này, tiếp tục swipe các thẻ danh bạ (8-11 nhịp). Do không có nút Like video, `_maybe_like_video` fail im lặng trong khi số nhịp swipe vẫn bị tính vào mẫu số, làm loãng tỷ lệ like toàn phiên.
  4. Selector nút Like cũ bắt buộc `clickable=="true"` trên element, bỏ lọt các container hoặc text desc hiển thị `"lượt thích"` / `"likes"`.

## 2. Giải Pháp Xử Lý
1. **Empty Feed Early Fallback:**
   - Bổ sung marker nhận diện: `"Hãy follow bạn bè"`, `"Tác giả nổi bật"`, `"Nhật ký"`, `"bạn sẽ nhận thấy họ ở đây"` vào `_FRIENDS_FEED_CONTENT_TERMS`.
   - Khi ở tab `friends` hoặc `following` mà phát hiện nội dung là gợi ý rỗng: lập tức điều hướng quay trở lại tab **Đề xuất (For You)** để tiếp tục lướt video thật, tránh lãng phí nhịp swipe trên danh sách gợi ý.
2. **Selector Nút Like & Telemetry Logging:**
   - Mở rộng selector nút Like: hỗ trợ kiểm tra `thích video`, `like video`, `thích`, `like`, và regex `thích` + `lượt thích`, `like` + `likes`.
   - Ghi nhận telemetry rõ ràng trong `log.jsonl`: `result="skipped", error="already_liked"` hoặc `error="button_not_found"` thay vì return False âm thầm.
3. **Cấu Hình Tỷ Lệ Like Chuẩn:**
   - `DEFAULT_FEED_LIKE_RATES`: Following nâng lên 50%, Friends nâng lên 80%.
