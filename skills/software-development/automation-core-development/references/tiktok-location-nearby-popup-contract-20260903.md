# TikTok In-App Location Permission Variant Contract ("Chưa có gì thu hút sự chú ý của bạn sao?")

## 1. Bối cảnh & Hiện tượng (Incident Case Máy 43 - 2026-09-03)
- Khi khởi động TikTok hoặc lướt Feed trên farm máy ảo / điện thoại thật, TikTok hiển thị modal hộp thoại hỏi quyền vị trí trong app:
  - **Tiêu đề (`id/ax_`):** `"Chưa có gì thu hút sự chú ý của bạn sao?"` (hoặc bản tiếng Anh: `"Nothing catching your attention?"` / `"Nothing catching your eye?"`).
  - **Nội dung (`android:id/message`):** `"Hãy cho phép truy cập vị trí để xem thêm các bài đăng liên quan lân cận."` (hoặc `"Allow access to location to see more relevant posts nearby."`).
  - **Nút từ chối (`android:id/button3`):** `"Hủy"` / `"Cancel"` (`bounds: [63, 1110][255, 1254]`, `clickable: true`).
  - **Nút mở cài đặt (`android:id/button1`):** `"Mở cài đặt"` / `"Open settings"` (`bounds: [699, 1110][1017, 1254]`, `clickable: true`).
- Nếu không có detector nhận diện, runner nuôi nick bị chặn ở màn hình popup, fail-closed với mã lỗi `GENERIC_POPUP_SCREEN` (`manual-needed:popup`) hoặc `STARTUP_TIMEOUT`.

## 2. Phân định ranh giới Core vs Hệ thống Android
- **Dialog quyền hệ thống Android:**
  - Package: `com.android.packageinstaller` / `com.google.android.permissioncontroller`.
  - Tiêu đề: `"Cho phép TikTok truy cập vị trí của thiết bị này?"`.
  - Cơ chế xử lý: `packageinstaller_permission` (tick checkbox `"Không hỏi lại"` tại `545, 1080` rồi bấm `"TỪ CHỐI"` tại `557, 1200`).
- **Dialog quyền vị trí In-App TikTok:**
  - Package: `com.ss.android.ugc.trill` / `com.zhiliaoapp.musically`.
  - Tiêu đề: `"Chưa có gì thu hút sự chú ý của bạn sao?"` / `"Xem nội dung phù hợp và địa điểm lân cận"`.
  - Cơ chế xử lý: `location_permission_dialog` trong `automation_core.tiktok.benign_popup`, `location_nearby_permission_vi` trong `automation_core.tiktok_popup`, và `_detect_location_prompt` trong `benign_popup_registry.py`.

## 3. Pitfalls & Anti-Patterns cần tránh
1. **Tránh Substring Collision với Dialog Hệ thống:**
   - Tuyệt đối **KHÔNG** dùng các từ khóa cụt/rộng như bare `"truy cập vị trí"` hay `"cho phép truy cập vị trí"` trong `_detect_location_prompt` nếu không có package guard. Vì dialog của Android packageinstaller chứa chuỗi `"Cho phép TikTok truy cập vị trí của thiết bị này?"` sẽ bị ăn khớp nhầm vào handler in-app, dẫn đến việc bỏ qua bước tick checkbox "Không hỏi lại".
   - Luôn thêm guard:
     ```python
     if "packageinstaller" in raw_xml or "permissioncontroller" in raw_xml:
         return False
     ```
2. **Action Mapping chuẩn:**
   - Action name trong `automation_core.tiktok.benign_popup` là `"dismiss_close_x"` (hoặc `"dismiss_deny_button"` tùy context adapter), mapping tới thao tác `tap(match.close_element)` (bấm `"Hủy"` / `"Cancel"`).
   - Tuyệt đối không bấm `"Mở cài đặt"` vì sẽ đưa máy sang ứng dụng Settings hệ thống làm vỡ flow.
3. **Sensitive Screen Fail-Closed Gate:**
   - Nếu trong hierarchy có trường `EditText` nhập mật khẩu/thông tin nhạy cảm, detector bắt buộc fail-closed trả về `None` để bảo vệ tài khoản.
