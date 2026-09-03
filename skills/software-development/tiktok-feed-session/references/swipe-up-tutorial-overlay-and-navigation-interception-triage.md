# Swipe-Up Tutorial Overlay & Navigation Interception Triage (Case 56)

## 1. Hiện tượng & Triệu chứng
- Máy farm dừng phiên với lỗi `manual-needed:account-switcher-not-open: screen after re-navigation is not profile root` hoặc tap vào tab Bottom Bar (Hồ sơ, Đề xuất) không có tác dụng.
- Hiện trường máy dừng tại TikTok FYP Feed nhưng hiển thị overlay hướng dẫn cử chỉ vuốt lần đầu: `tv_strengthen_swipe_up_guide` ("Vuốt lên để xem thêm" / "Swipe up to see more").

## 2. Nguyên nhân (Anti-Pattern)
1. **Overlay đánh chặn sự kiện chạm (Touch Interception):** Tutorial overlay che toàn màn hình khiến mọi tọa độ tap vào Bottom Bar (Navigation) đều bị overlay hấp thụ và không truyền xuống app TikTok.
2. **Stale Target Coordinates (TOCTOU):** Nếu detector phát hiện target navigation từ XML cũ trước khi popup/overlay xuất hiện, việc tiếp tục tap tọa độ cũ mà không reset `point = None` sẽ dẫn đến bấm mù vào overlay.
3. **Drift Re-navigation bị chặn:** Trong luồng switch profile (`_capture_profile_switcher_xml_with_add_phone_guard`), sau khi drift về Feed và re-navigate, overlay tutorial chặn tap làm màn hình vẫn ở Feed thay vì Profile root.

## 3. Quy tắc xử lý chuẩn (Standard Fix)

### A. Đăng ký Benign Popup Handler
- Tên handler: `swipe_up_tutorial_overlay` (Priority 89).
- **Detector:**
  - Nhận diện `tv_strengthen_swipe_up_guide`, `swipe_up_guide` hoặc các cụm từ `"vuốt lên để xem thêm"`, `"swipe up to see more"`.
  - Guard: Chỉ chấp nhận node thuộc package TikTok; fail-closed nếu màn hình thuộc launcher hoặc multi-window dialog khác.
- **Dismisser:**
  - Tính toán tọa độ vuốt dọc theo kích thước màn hình thực tế (tỷ lệ $y_{start} = 73\% \to y_{end} = 21\%$, hoặc $540, 1400 \to 540, 400$ trên 1080x1920).
  - Kiểm tra kết quả lệnh swipe trả về thành công trước khi báo `dismissed=True`.

### B. Pre-Navigation Overlay Clearing (`calibrate_screens.py`)
- Trước khi tap navigation target: Nếu XML chứa overlay thuộc allowlist (`swipe_up_tutorial_overlay`, `location_permission_prompt`, v.v.):
  1. Reset ngay `point = None` và `selector = None` để tránh TOCTOU tap vào tọa độ che khuất.
  2. Gọi dismisser giải phóng overlay.
  3. Bắt buộc recapture XML mới và tìm lại target navigation.
  4. Nếu dismisser thất bại hoặc gặp exception: Trả về `CalibrationResult(ok=False, ...)` fail-closed, không được tiếp tục tap tọa độ cũ.

### C. Profile Switcher Drift Re-Navigation (`feed_swipe_smoke.py`)
- Nếu sau khi re-navigate Profile mà màn hình vẫn chưa phải là Profile root:
  1. Kiểm tra `find_matching_handler` với allowlist handler lành tính an toàn.
  2. Thực hiện dismiss overlay và re-navigate Profile lần 2.
  3. Ghi log tường minh nếu gặp lỗi, không nuốt exception bằng pass trần.

### D. Keyboard State Fail-Closed Logic
- Khi `dumpsys input_method` command failed hoặc output rỗng: Bắt buộc trả về `KeyboardState(visible=None)`.
- Consumer chỉ được phép coi bàn phím đã đóng khi kiểm tra tường minh `keyboard_state.visible is False`.
