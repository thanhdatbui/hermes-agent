# UI Popup Pitfalls: Live Streams, Share Sheet & Contact Suggestion False Positives

## 1. False Positive trong `detect_contact_follow_suggestion`
- **Hiện tượng**: Máy dừng với status `manual-needed:popup` và log ghi `unexpected popup/dialog marker detected` hoặc `known contact_follow_suggestion popup detected` trên video bình thường hoặc livestream.
- **Root cause**: Bộ từ khóa nhận diện danh bạ / gợi ý bạn bè quá lỏng. Ví dụ: từ khóa `"mời bạn"` bắt nhầm câu chat thông thường của người xem hoặc chủ livestream (*"Nhà có tiệc, mời bạn chung vui!"*). Kết hợp với nút "Follow <Channel>" sẵn có trên livestream, detector nhận nhầm thành thẻ gợi ý kết bạn.
- **Quy tắc**:
  - Tuyệt đối KHÔNG dùng các cụm từ ngắn, thông dụng trong tiếng Việt như `"mời bạn"` làm marker độc lập.
  - Bắt buộc dùng các cụm từ đầy đủ mang tính danh bạ/bạn bè: `"mời bạn bè"`, `"thêm bạn bè"`, `"bạn bè với"`, `"đồng bộ danh bạ"`.

## 2. Kẹt Bottom Sheet "Gửi đến" / Share Sheet (`share_sheet`)
- **Hiện tượng**: Máy kẹt với status `manual-needed` sau các bước tương tác (dismiss card, tap gần mép phải), log báo `manual review required after contact_follow_suggestion dismiss: unknown`.
- **Root cause**: App TikTok vô tình chạm vào nút Chia sẻ (hoặc cử chỉ swipe kéo nhầm panel chia sẻ), làm bung Bottom Sheet "Gửi đến" (`com.ss.android.ugc.trill:id/tv_title`, `w61: Sao chép Liên kết`). Classifier không có rule nhận diện màn hình này nên rơi vào `unknown`.
- **Xử lý chuẩn trong `automation_core/tiktok/benign_popup.py`**:
  - Thêm `detect_share_sheet(root)`: Quét `id/tv_title` có text `"Gửi đến"` / `"Send to"` hoặc content-desc `"trang tính dưới cùng"` / `"bottom sheet"` kết hợp với marker `"sao chép liên kết"` / `"copy link"`.
  - Gán action an toàn: `press_back`. Khi gặp share sheet, bot gửi phím `BACK` Android để hạ sheet xuống trở về feed mà không làm thoát app.

## 3. Yêu cầu Test khi bổ sung Popup Detector
Khi sửa hoặc thêm detector trong `automation-core`:
- Bắt buộc có đủ 3 loại test trong `tests/test_tiktok_benign_popup.py`:
  1. **Positive test**: Chứng minh XML thực tế match đúng `popup_type` và gán đúng action (ví dụ `press_back`).
  2. **Negative test**: Chứng minh text gần giống nhưng không phải popup thì trả về `None`.
  3. **Regression test**: Chứng minh từ khóa lỏng đã bị loại bỏ không còn match sai câu chat thường, trong khi các từ khóa chuẩn vẫn match đúng.
