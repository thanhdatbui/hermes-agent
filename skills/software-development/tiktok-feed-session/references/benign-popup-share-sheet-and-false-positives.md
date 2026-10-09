# Pitfalls: Benign Popup False Positives & Share Sheet Dismissal

## 1. Tránh từ khóa nhận diện quá rộng trong `detect_contact_follow_suggestion`
- **Hiện tượng**: Máy lướt feed gặp LIVE stream (hoặc video có comment/caption bình thường) thì bị kẹt ở `manual-needed:popup` hoặc `unexpected popup/dialog marker detected`.
- **Nguyên nhân gốc rễ**:
  - Trong `detect_contact_follow_suggestion` (`automation_core/tiktok/benign_popup.py`), các từ khóa quá ngắn hoặc thông dụng như `"mời bạn"` sẽ match nhầm các câu chat trong phòng LIVE stream (ví dụ: *"Nhà có tiệc, mời bạn chung vui!"*) hoặc caption video.
  - Kết hợp với sự hiện diện của nút Follow trên thanh điều hướng phòng LIVE, detector ngộ nhận đây là popup gợi ý kết bạn danh bạ và cố gắng tìm cách đóng/bấm nút, dẫn đến fail-closed `manual-needed`.
- **Giải pháp**:
  - Tuyệt đối không dùng cụm từ chung chung như `"mời bạn"`. Bắt buộc dùng cụm từ chuẩn ngữ cảnh danh bạ: `"mời bạn bè"`, `"thêm bạn bè"`, `"đồng bộ danh bạ"`.

## 2. Xử lý Bottom Sheet "Gửi đến" / Share Sheet (`share_sheet`)
- **Hiện tượng**:
  - Máy sau khi đóng thẻ gợi ý bạn bè hoặc vô tình chạm vào nút chia sẻ thì màn hình hiện bảng bottom sheet "Gửi đến" (`com.ss.android.ugc.trill:id/tv_title` = "Gửi đến" / "Send to", kèm "Sao chép Liên kết").
  - Màn hình bị phân loại thành `unknown`, lệnh vuốt lên (swipe) không thể đóng bottom sheet này, làm máy kẹt tại `manual review required after contact_follow_suggestion dismiss: unknown`.
- **Giải pháp**:
  - Đăng ký `detect_share_sheet` trong `detect_allowed_generic_popup` (`automation_core/tiktok/benign_popup.py`).
  - Gắn action tương ứng là `"press_back"` (`input keyevent BACK`). Phím BACK trên Android sẽ hạ bottom sheet ngay lập tức và đưa ứng dụng trở lại luồng lướt feed bình thường.

## 3. Kỷ luật phản hồi Coordinator
- Khi người dùng phát lệnh "Làm đi", Coordinator phải ngay lập tức tiến hành điều tra hiện trường qua inspect / log thật, thực thi bản vá và chạy test nghiệm thu ngay; không dừng lại hỏi xin phép lặp lại hay chần chừ gây gián đoạn phiên ("??").
