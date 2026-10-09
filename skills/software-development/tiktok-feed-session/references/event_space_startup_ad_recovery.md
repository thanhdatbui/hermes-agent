# Recovery: Màn hình "Không gian sự kiện" (Event Space Startup Interstitial)

## Hiện tượng (Symptom)
- Runner báo alert: `startup ad/splash marker detected` (hoặc `startup ad/splash remained after skip attempts`).
- Màn hình hiện tại hiển thị tiêu đề "Không gian sự kiện" (hoặc "Event Space"), chứa danh sách sự kiện/live cards (ví dụ: MEGALIVE NGÀY ĐÔI, Đăng ký...), và nút quay lại (`←` / `Quay lại` / `Navigate up`) ở góc trên bên trái.

## Nguyên nhân gốc rễ (Root Cause)
1. **Phân loại màn hình**: Trong `core/safety.py`, trạng thái `manual-needed:startup-ad` phát hiện đây là interstitial quảng cáo/sự kiện lúc mở app.
2. **Cơ chế skip bị nghẽn**: Trong `flows/feed_swipe_smoke.py`, hàm `_startup_ad_skip_selector()` chỉ tìm kiếm các nút bỏ qua quảng cáo truyền thống (`Bỏ qua quảng cáo`, `Skip ad`, `Vuốt lên để bỏ qua`, nút đóng `X`).
3. **Không tìm thấy nút Skip**: Màn hình "Không gian sự kiện" sử dụng thanh tiêu đề với nút điều hướng `←` (`content-desc="Quay lại"` hoặc `Navigate up`) thay vì nút "Bỏ qua". Do đó, `_startup_ad_skip_selector()` trả về `None`, dẫn đến `_mark_startup_ad_stuck()` và dừng flow với mã `manual-needed`.

## Giải pháp phục hồi chuẩn (Standard Recovery Pattern)
1. **Trong `flows/feed_swipe_smoke.py` (`_startup_ad_skip_selector`)**:
   - Bổ sung kiểm tra tiêu đề/text chứa `"Không gian sự kiện"` hoặc `"Event Space"`.
   - Khi phát hiện, tìm element điều hướng quay lại ở góc trên bên trái (`content-desc` là `Quay lại`, `Back`, `Navigate up` hoặc element clickable ở góc trên bên trái) để thực hiện `tap_back` hoặc `navigate_back`.
2. **Trong `flows/benign_popup_registry.py` & `flows/benign_popup.py`**:
   - Đăng ký detector cho `detect_event_space_overlay(root)` kiểm tra text `"Không gian sự kiện"`.
   - Action dismiss: Tap vào nút back ở header hoặc gửi keyevent `KEYCODE_BACK` có kiểm tra an toàn để quay về video feed.
