# TikTok Upload Interrupted Draft Recovery

## Bối cảnh & Hiện tượng
Khi đang trong quá trình upload video trên TikTok (đặc biệt trên Samsung farm Android 7/S7), do gián đoạn mạng, crash nhẹ, hoặc timeout điều hướng, TikTok có thể tự động lưu video vào mục "Bản nháp" (Drafts) và hiển thị banner hoặc nút "Bản nháp" ngay trên trang Profile / màn hình chọn video.
- Trước đây: Quy trình `_delete_all_profile_drafts` hoặc dismiss popup thường xóa sạch bản nháp hoặc bấm back bỏ qua.
- Yêu cầu mới: Khi gặp trường hợp đăng video dở chừng hiện bản nháp, cần tự động tap vào bản nháp để mở lại composer và bấm đăng tiếp thay vì hủy bỏ hoặc cố upload lại từ đầu gây trùng lặp/kẹt máy.

## Quy tắc xử lý UI
1. **Phát hiện màn hình Bản nháp / Draft tile**:
   - Quét XML qua ATX session (`dumpWindowHierarchy [true]`).
   - Nhận diện text `"Bản nháp"` / `"Drafts"` hoặc tile bản nháp đầu tiên trong lưới Profile / creation view.
2. **Kích hoạt Draft & Tiếp tục Đăng**:
   - Tap vào bản nháp vừa tạo (`_tap_if_found(xml, text_contains="Bản nháp")`).
   - Chờ composer render (nhận diện nút `"Tiếp"`, `"Đăng"`, `"Post"`).
   - Tiếp tục luồng `CAPTION_FILL` / `POST` thông thường.
3. **Fail-safe**:
   - Nếu vào màn nháp nhưng không tìm thấy nút Đăng hoặc bản nháp bị hỏng: thoát an toàn bằng phím BACK, ghi log rõ ràng và chuyển sang luồng dự phòng, tránh kẹt lặp vô hạn.
