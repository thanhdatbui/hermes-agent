# Bottom Sheet Mutual Follow Navigation Blocker Recovery ("Đã follow chung")

## Hiện tượng & Cảnh báo (Symptom)
- Cảnh báo P0: `profile verification navigation-failed: navigation target profile not found in XML` xuất hiện tại bước kết thúc chu kỳ lướt feed (`feed-session-smoke/tap_profile` -> `verify_profile`).
- Màn hình bị kẹt lại tại popup dạng Bottom Sheet (`FrameLayout: content-desc="Trang tính dưới cùng"` che khuất nửa dưới `[0, 1266][1080, 1920]`).

## Cơ chế lỗi kép (Double-Fault Mechanism)

1. **Sai lệch phân loại màn hình (`core/classifier.py`):**
   - Biến `following_terms` bị gán thừa chuỗi `"\u0110\u00e3 follow"` ("Đã follow").
   - Trong TikTok tiếng Việt:
     - Tab feed là **"Đang Follow"** (Following) hoặc "Following".
     - **"Đã follow"** là nhãn trạng thái của nút bấm quan hệ người dùng (User Follow Button State), xuất hiện phổ biến trong danh sách gợi ý tài khoản và Bottom Sheet.
   - Khi Bottom Sheet xuất hiện có nút bấm "Đã follow", hàm `classify_tiktok_screen` quét trúng và kết luận màn hình đang ở tab feed `following` (confidence 0.8).

2. **Triệt tiêu sai phím Back (`flows/calibrate_screens.py`):**
   - Hàm `navigate_to` khi chuyển sang `NavigationTarget.PROFILE` kiểm tra:
     ```python
     if current_classification.screen in {"home", "for-you", "following", "friends"}:
         is_home_or_feed = True
     ```
   - Khi `is_home_or_feed = True`, hệ thống ghi log `navigation_back_recovery_skipped_at_home_feed` ("app is already at home/feed, skipping KEYCODE_BACK to prevent exit to launcher") và **cố tình bỏ qua lệnh Back recovery**.
   - Hậu quả: Popup không bao giờ được đóng bằng phím Back -> thanh Bottom Navigation Bar (`Hồ sơ` / `Profile`) tiếp tục bị che khuất -> tìm XML trả về `not-found`.

3. **Lỗ hổng Registry nhận diện Popup (`flows/benign_popup_registry.py` & `benign_popup.py`):**
   - `_detect_follow_friends` thiếu marker `"Đã follow chung"`, `"Follow chung"`.
   - `_find_follow_friends_semantic_close_control` chỉ tìm nút đóng có text/desc "Đóng"/"Close" hoặc resource-id cố định, không nhận diện được nút `X` dạng `ImageView` clickable ở góc trên bên phải của Bottom Sheet (`x >= 800`, `abs(y - title_y) <= 150`).

## Quy tắc & Khắc phục chuẩn (Invariants & Fix Pattern)

1. **Kỷ luật nhãn Tab Feed:**
   - Tuyệt đối không đưa `"Đã follow"` vào tập từ khóa tab feed (`following_terms`). Tab feed chỉ chứa: `"Following"`, `"Đang Follow"`, `"\u00c4\u0090ang Follow"`.
2. **Đăng ký Popup "Đã follow chung":**
   - Bổ sung `"Đã follow chung"`, `"Follow chung"` vào markers của `_detect_follow_friends` (ưu tiên 81: `follow_friends_suggestion_popup`).
   - Cập nhật bộ tìm kiếm `close_target`: nếu là Bottom Sheet có `title_node` ("Đã follow chung", "Follow chung"), nhận diện nút đóng `X` là `ImageView`/`ImageButton` clickable ở góc trên bên phải header sheet.
3. **Fallback phím Back an toàn:**
   - Khi không tìm thấy close control ngữ nghĩa trên sheet, luôn thực thi fallback bấm `KEYCODE_BACK` (`send_device_back_key`) để hạ Bottom Sheet xuống trước khi phán quyết lỗi điều hướng.
