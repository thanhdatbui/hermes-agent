# Swipe-Up Tutorial Overlay & Navigation Overlay Handling (Case 56)

## 1. Hiện tượng & Bối cảnh
- **Lỗi hiện trường:** Máy dừng phiên với lỗi `manual-needed:account-switcher-not-open: screen after re-navigation is not profile root` và giữ hiện trường.
- **Nguyên nhân gốc rễ:**
  1. Trên TikTok FYP Feed xuất hiện overlay hướng dẫn cử chỉ vuốt "Vuốt lên để xem thêm" / "Swipe up to see more" (`tv_strengthen_swipe_up_guide`, `swipe_up_guide`). Overlay này đánh chặn toàn bộ sự kiện chạm vào thanh điều hướng đáy (Profile tab).
  2. Khi `verify_and_switch_profile` thực hiện chuyển tài khoản hoặc sau khi bấm BACK drift về Feed, `_navigate_profile_for_preflight` tap vào nút "Hồ sơ" nhưng cử chỉ chạm bị overlay tutorial chặn lại -> TikTok vẫn ở Feed.
  3. `_is_profile_root_screen` sau re-navigation trả về False và báo dừng phiên.

## 2. Quy tắc an toàn bắt buộc khi xử lý Gesture/Tutorial Overlay

### A. Negative Exclusions trên FYP (Tránh False-Negative trên Tiếng Anh)
- **Cấm:** Không được loại trừ toàn bộ XML chỉ vì xuất hiện từ `"following"` hoặc `"follower"`. Tab "Following" nằm cố định trên thanh điều hướng đầu trang của FYP TikTok tiếng Anh (`Following | For You`).
- **Chuẩn:** Chỉ loại trừ khi có tổ hợp dấu hiệu chỉnh sửa hồ sơ / đăng nhập / nhạy cảm rõ ràng:
  `"sửa hồ sơ"`, `"edit profile"`, `"profile views"`, `"số lượt xem hồ sơ"`, `"chia sẻ hồ sơ"`, `"share profile"`, `"thêm tiểu sử"`, `"add bio"`, `"đăng nhập"`, `"login"`, `"xác minh"`, `"password"`.

### B. Fail-Closed cho OCR Fallback
- OCR tuyệt đối KHÔNG được match tutorial overlay nếu XML hiện tại thuộc về app khác hoặc dialog hệ thống foreground (`com.google.android.gms`, `com.android.permissioncontroller`, `com.android.settings`).
- Chỉ đánh giá OCR khi XML đã xác nhận ngữ cảnh TikTok (`_is_tiktok_context_element`) và OCR chứa marker tường minh trong `SWIPE_UP_TUTORIAL_MARKERS`.

### C. Dismisser tính theo tỷ lệ màn hình động & Bounded Polling
- **Tọa độ động:** Luôn lấy kích thước màn hình động từ `ctx.device.window_size()`, `adb shell wm size`, hoặc `ctx.config` (`screen_width`, `screen_height`). Tính tọa độ swipe dọc theo tỷ lệ: `x = 50% width`, `y_start = 73% height`, `y_end = 21% height`.
- **Bounded Polling:** Sau khi vuốt, bắt buộc capture lại XML (`ctx.dump_hierarchy()`) và parse kiểm chứng (`_detect_swipe_up_tutorial`).
  - Nếu recapture thất bại / XML invalid -> trả `PopupDismissResult(dismissed=False, popup_closed=False)`.
  - Nếu sau 3 lần poll overlay vẫn còn -> trả `PopupDismissResult(dismissed=False, popup_closed=False)`.
  - Chỉ trả `dismissed=True, popup_closed=True` khi xác nhận overlay đã biến mất.

### D. Đồng nhất Contract Navigation & Chống TOCTOU
- Trong `tap_navigation_target` (`calibrate_screens.py`):
  - Reset `point = None` và `selector = None` ngay khi phát hiện overlay trước khi gọi dismisser để chống TOCTOU race condition.
  - Sau khi dismiss và recapture, phải re-verify rằng overlay đã biến mất trước khi tìm navigation element.
  - Mọi nhánh dismiss thất bại và exception trong `tap_navigation_target` phải trả về đúng kiểu `NavigationResult(False, "fail", ...)` với `selector=None, point=None`.

### E. Chuẩn hóa Alias Package cho Focus Check
- Cả `post_relaunch` và `recheck_focus` đều phải đọc đủ các alias: `package`, `focused_package`, `focus_package` (cả ở root dict lẫn trong `extra`), chuẩn hóa `strip().lower()` trước khi so khớp với `tiktok_pkgs`.
