# TikTok AI Label Bottom Sheet Recovery & Safe Feed Swipe Coordinate Boundary (06/09/2026 - Case 129)

## 1. Hiện tượng & Triệu chứng
- **Alert:** `TikTok startup/loading screen detected; swipe recovery (2 swipes) still stuck`.
- **Màn hình thực tế:** Bottom sheet modal "Thông tin về AI" ("Bài đăng được nhà sáng tạo gắn nhãn") bung lên từ đáy màn hình.
- **Tác động:** Modal che toàn bộ nửa dưới màn hình feed và chặn touch event của video, khiến lệnh cuộn video bị vô hiệu hóa. Script nhận định màn hình không thay đổi sau swipe và báo kẹt loading / recovery failed.

## 2. Nguyên nhân kích hoạt (Root Cause)
- **Vị trí Badge AI:** Nằm ở góc dưới bên trái màn hình ($X \in [40, 380]$, $Y \in [1380, 1520]$ trên độ phân giải $1080 \times 1920$). Đây là ViewGroup/Button có thuộc tính `clickable="true"`.
- **Cơ chế kích hoạt:** Thao tác vuốt feed (`feed_swipe`) khi có jitter hoặc điểm bắt đầu (`ACTION_DOWN`) rơi vào vùng $X < 380, Y \approx 1400-1500$, ngón tay ảo hạ xuống trúng badge AI trước khi sinh chuyển động kéo. Do độ trễ ngưỡng vuốt (touch slop) hoặc máy lag, hệ điều hành nhận diện là thao tác click và bung bottom sheet modal.

## 3. Tọa độ an toàn cho Feed Swipe
- **Trục X (Ngang):** Khóa chặt dải trung tâm màn hình $X \in [480, 600]$:
  + Tránh dải trái $X < 380$ (nơi chứa nhãn AI, username, caption).
  + Tránh dải phải $X > 850$ (nơi chứa cột nút Tim, Comment, Bookmark, Share).
- **Trục Y (Dọc):** Vuốt từ $Y_{start} \approx 1350$ lên $Y_{end} \approx 450$.

## 4. Handler tự động đóng Popup (`benign_popup_registry.py`)
- **Detection (`_detect_ai_info_bottom_sheet`):** Kiểm tra XML và OCR text với các từ khóa:
  + Tiếng Việt: "thông tin về ai", "bài đăng được nhà sáng tạo gắn nhãn", "chỉnh sửa bằng ai", "nội dung này được tạo hoặc chỉnh sửa bằng ai".
  + Tiếng Anh: "ai-generated", "ai info", "creator labeled".
- **Dismissal (`_dismiss_ai_info_bottom_sheet`):**
  1. Thử click icon close (✕) hoặc nút có text/content-desc "Đóng", "Close", "Quay lại".
  2. Fallback gửi phím `BACK` (`ctx.press_back()` / `keyevent 4` / `send_device_back_key`).
  3. **Fail-Closed Verification:** Kiểm tra `action_performed` và chụp lại hierarchy (`post_xml = _safe_capture_hierarchy(ctx)`). Nếu popup vẫn còn, trả về `dismissed=False, reason="ai_info_still_present_after_dismiss"`.
- **Registry Entry:** Tên `"tiktok_ai_info_bottom_sheet"`, priority `68`.
