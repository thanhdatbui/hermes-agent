# Video Playback Options Sheet / Long Press Menu Dismissal (Case 66)

## 1. Hiện tượng & Bản chất lỗi
- **Hiện tượng:** Máy nuôi acc dừng phiên giữa chừng với cảnh báo:
  `unknown TikTok state; swipe recovery (2 swipes) still stuck` và giữ hiện trường `GIỮ HIỆN TRƯỜNG ĐỂ HERMES AGENT XỬ LÝ`.
- **Bản chất:** Trong quá trình lướt Feed video, thao tác vuốt/chạm vô tình bị TikTok nhận diện là nhấn giữ (long-press), làm mở Bottom Sheet menu cài đặt phát video (*Video Playback Options Sheet*):
  - Tiếng Việt: "Loại bỏ các yếu tố trên màn hình", "Cuộn tự động", "Phụ đề và dịch thuật", "Chiếu", "Ảnh trong ảnh", "Âm thanh nền", "Lý do bạn thấy".
  - Tiếng Anh: "Clear display", "Auto scroll", "Subtitles and translation" / "Captions", "Cast", "Picture-in-picture", "Background audio", "Why you're seeing this".
- **Anti-Pattern:** Bottom sheet modal che phủ 50-60% nửa dưới màn hình khiến feed detector không nhận diện được Feed. Lệnh `swipe_recovery_on_stuck` (swipe dọc) chỉ cuộn danh sách menu hoặc bị bottom sheet chặn touch chứ không đóng được dialog.

## 2. Giải pháp chuẩn hóa (Case 66)
1. **Benign Popup Registry:**
   - Đăng ký handler `video_playback_options_overlay` với độ ưu tiên cao (priority 83) trong `flows/benign_popup_registry.py` và `core/benign_popup.py`.
2. **Detection Rule:**
   - Multi-marker matching: Bắt buộc tối thiểu 2 markers thuộc danh sách cài đặt phát video (hoặc marker đặc thù "Loại bỏ các yếu tố trên màn hình" / "Clear display" / "Cuộn tự động" + "Ảnh trong ảnh").
   - Negative Exclusions: Tuyệt đối không match màn hình Profile ("Sửa hồ sơ", "Đã follow"), Login, Captcha, Password, hoặc caption text của video.
3. **Dismissal Protocol:**
   - Primary: Gửi phím `BACK` (`KEYCODE_BACK` / 4) đóng modal ngay lập tức về Feed video mà không thoát khỏi ứng dụng TikTok.
   - Fallback: Tap vào vùng trống phía trên màn hình `(w // 2, int(h * 0.2))`.
   - Xác thực lại hierarchy đảm bảo `popup_closed=True`.
