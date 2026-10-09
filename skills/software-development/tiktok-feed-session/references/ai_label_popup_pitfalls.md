# Pitfall & Quy chuẩn xử lý Popup 'Thông tin về AI' (AI Label / Information Modal)

## 1. Hiện tượng & Bản chất
Khi lướt video TikTok, một số video có chứa nhãn/chip nhỏ góc dưới bên trái:
- **Nội dung nhãn:** "Thông tin về AI" / "Có chứa nội dung do AI tạo" / "Nội dung do AI tạo".
- **Vị trí hiển thị:** Bounding box thường nằm ở góc dưới bên trái, phía trên caption/username và dưới vùng video trung tâm:
  - Tọa độ thông thường (màn hình 1080x1920): `X: 40 - 380`, `Y: 1380 - 1520`.
- **Đặc tính Android:** Chip này là một `ViewGroup` / `Button` có `clickable="true"`.
- **Lý do kích hoạt nhầm:**
  - Thao tác Feed Swipe (`adb shell input swipe`) nếu có jitter hoặc điểm bắt đầu (`start_x`) bị lệch sang trái ($X < 380$), ngón tay ảo hạ xuống (`ACTION_DOWN`) sẽ chạm đúng diện tích của nhãn AI.
  - Nếu máy bị delay/lag trước khi ngón tay kịp trượt (chưa vượt `touch slop`), TikTok và hệ thống Android sẽ ghi nhận thành một cú TAP/CLICK vào nhãn AI.
  - Ngay lập tức, TikTok bung bottom-sheet modal popup: *"Thông tin về AI"* (giải thích về nội dung do AI tạo) che toàn bộ nửa dưới màn hình và vô hiệu hóa các thao tác lướt tiếp theo.

## 2. Vùng tọa độ an toàn cho Feed Swipe (Safe Corridor)
Để không bao giờ kích hoạt nhầm badge AI, nhãn quảng cáo, hoặc các nút tương tác:
- **Trục X (Ngang):** Khóa chặt ở dải trung tâm màn hình **$X \in [480, 600]$**.
  - Tránh tuyệt đối $X < 380$: Nơi chứa nhãn AI, Avatar creator nhỏ, Caption, Username.
  - Tránh tuyệt đối $X > 850$: Cột nút tương tác (Like/Heart, Comment, Bookmark, Share, Âm thanh).
- **Trục Y (Dọc):** Vuốt từ $Y_{start} \approx 1350$ lên $Y_{end} \approx 450$ với thời gian swipe dứt khoát ($200 - 350$ms) để tránh bị nhận diện thành Long-press hay Tap.

## 3. Quy tắc Auto-Dismiss trong `benign_popup_registry.py`
Nếu popup đã bung ra do video trước hoặc do TikTok chủ động gợi ý:
- **Detection text:**
  - `"Thông tin về AI"`
  - `"Nội dung do AI tạo"`
  - `"Giới thiệu về nội dung do AI tạo"`
  - `"About AI-generated content"`
- **Hành động đóng (Dismiss action):**
  - Gửi phím `BACK` (Android Keyevent 4) để hạ bottom-sheet modal về lại video feed.
  - Fallback: Tap vào vùng trống nửa trên màn hình ($X: 540, Y: 300$) để dismiss overlay.
