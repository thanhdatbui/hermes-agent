# TikTok Post Audience Confirmation Popup Recovery

## Hiện tượng & Nguyên nhân gốc
Khi đăng video trên TikTok (đặc biệt các tài khoản mới đăng hoặc có thay đổi cài đặt khán giả), sau khi bấm nút **"Đăng"** / **"Post"**, TikTok hiển thị một modal xác nhận quyền riêng tư trước khi thực sự tải video lên:
- **Tiêu đề**: `Xác nhận rằng “Mọi người” có thể nhìn thấy bài đăng của bạn` (English: `Confirm that "Everyone" can see your post` / `everyone can view your post`).
- **Nội dung**: `Cài đặt trước đó cho phép bạn chia sẻ bài đăng với “Mọi người”, do đó “Mọi người” có thể nhìn thấy bài đăng này. Bạn có thể thay đổi cài đặt đối tượng khán giả nếu muốn người khác nhìn thấy bài đăng này.`
- **Nút hành động**:
  - `Thay đổi` (Change)
  - `Xác nhận` (Confirm - nút màu đậm/chính)

## Rủi ro nếu thiếu handler
- Trong vòng lặp `_wait_for_post_submission()`, script kiểm tra xem giao diện composer đã biến mất chưa.
- Modal xác nhận khán giả che trên bề mặt composer khiến luồng không ghi nhận được submission thành công, sau 15 lần poll (~30s-45s) sẽ bị kết luận là `POST_SUBMISSION_UNKNOWN` hoặc `NOT_ACCEPTED` và fail-closed về `MANUAL_REVIEW`.
- Video thực tế chưa được đăng lên vì TikTok đang đợi người dùng nhấn nút "Xác nhận".

## Giải pháp triển khai chuẩn (StateMachine)
1. **Phương thức nhận diện & xử lý**:
   - Tên hàm: `_dismiss_audience_confirmation_popup(adapter, xml_text: str) -> bool`.
   - Chuẩn hóa: `lowered = (xml_text or "").casefold()`.
   - Markers nhận diện:
     - Tiếng Việt: `"xác nhận rằng"` kết hợp với `"mọi người"`, `"nhìn thấy bài đăng"`.
     - Tiếng Anh: `"confirm that"` kết hợp với `"can see your post"` hoặc `"can view your post"`.
   - Thao tác: Bấm vào nhãn `"Xác nhận"` hoặc `"Confirm"` (hỗ trợ cả thuộc tính `text` lẫn `content_desc`).
   - Cấm bấm tọa độ mù, cấm bấm Back (vì Back sẽ hủy việc đăng và đóng modal).

2. **Vị trí tích hợp**:
   - Gọi ngay sau `xml_text = adapter.dump_ui()` trong `_wait_for_post_submission(adapter)`.
   - Nếu trả về `True`, `time.sleep(1)` và `continue` vòng lặp để tiếp tục theo dõi tiến trình submit cho đến khi rời composer.

3. **Kiểm thử bắt buộc (Focused Test)**:
   - Test case dương tính: XML chứa đúng modal và nút `Xác nhận` -> adapter ghi nhận tap và trả về `True`.
   - Test case âm tính: XML bình thường hoặc không liên quan -> trả về `False`, không tap nhầm.
