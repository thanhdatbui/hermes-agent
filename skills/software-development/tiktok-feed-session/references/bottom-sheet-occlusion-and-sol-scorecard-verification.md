# Bottom Sheet Occlusion of Profile Navigation & Sol Scorecard Verification

## 1. Bản chất sự cố Bottom Sheet Occlusion (Hiện trường Máy M43)
- **Triệu chứng**: Farm Alert báo `profile verification navigation-failed: navigation target profile not found in XML` thuộc taxonomy `login/GMS/verification`.
- **Nguyên nhân gốc rễ**: Sau khi lướt feed xong (hoặc sau một số tương tác), TikTok bung một cửa sổ **Bottom Sheet** (`FrameLayout: content-desc="Trang tính dưới cùng"`, bounds: `[0, 1266][1080, 1920]`) có tiêu đề `"Đã follow chung (1)"` hoặc gợi ý kết bạn.
- **Cơ chế lỗi kép (Double Fault)**:
  1. Cửa sổ Bottom Sheet đè lên nửa dưới màn hình, che mất toàn bộ thanh điều hướng Bottom Navigation Bar chứa tab "Hồ sơ" (Profile).
  2. Nút bấm trong sheet có chữ `"Đã follow"` làm bộ phân loại màn hình (`classify_tiktok_screen`) nhận diện nhầm thành feed tab `following`.
  3. Khi điều hướng sang Profile, hệ thống thấy đang ở feed nên skip phím `Back` (`navigation_back_recovery_skipped_at_home_feed`), dẫn đến không thể tự dismiss popup và không thể tìm thấy tab Profile trong XML.

## 2. Giải pháp kỹ thuật chuẩn
1. **Benign Popup Detection (`flows/benign_popup_registry.py` & `flows/benign_popup.py`)**:
   - Thêm marker `"Đã follow chung"` và `"Follow chung"` vào danh mục popup bạn bè lành tính.
   - Nhận diện tiêu đề Bottom Sheet và tự động tìm nút đóng `X` (`ImageView` / `ImageButton` ở góc trên header sheet: `bounds[0] >= 800` và `abs(bounds[1] - t_bounds[1]) <= 150`) để click đóng sheet.
2. **Overlay Guard trong Navigation (`flows/calibrate_screens.py`)**:
   - Khi kiểm tra `is_home_or_feed` trước khi gửi `KEYCODE_BACK`: Nếu trên UI đang xuất hiện Bottom Sheet (`content-desc="Trang tính dưới cùng"` hoặc `resource-id` chứa `"g1i"` hoặc class chứa `"dialog"`), **CẤM** coi là Home/Feed sạch.
   - Bắt buộc đặt `is_home_or_feed = False` để cho phép phím `Back` thực thi giải phóng lớp phủ trước khi tìm tab điều hướng.

## 3. Quy trình vượt Sol Auditor Scorecard (>= 85đ) khi chốt phiên
- **Điểm nghẽn**: Sol Auditor chấm rất khắt khe phần `Test Evidence` (yêu cầu >= 20/25đ) và sẽ REJECT nếu patch heuristic UI mà không có test diff / fixture chứng minh.
- **Kinh nghiệm vượt Gate**:
  - BẮT BUỘC thêm ít nhất 1 regression unit test sử dụng đúng XML fixture trích xuất từ hiện trường thực tế vào `tests/test_benign_popup_registry.py`.
  - Kiểm chứng cả 2 chiều: `detect_follow_friends_suggestion_popup(root) is True` VÀ `_find_follow_friends_semantic_close_control(root)` trích xuất đúng bounds nút đóng.
  - Khi có test evidence đầy đủ trong git diff, điểm `Test Evidence` sẽ nhảy từ 12đ lên 23đ, đưa tổng điểm lên 88đ (Approved).
