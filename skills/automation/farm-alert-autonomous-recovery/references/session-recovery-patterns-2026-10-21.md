# Farm Alert Recovery Patterns (2026-10-21 Row 8 Incident)

## 1. Classifier Unknown Screen Trap
- **Triệu chứng:** TikTok dừng phiên với `manual-needed: unknown TikTok state` ngay sau khi chuyển tài khoản hoặc vào feed.
- **Nguyên nhân:** Popup lành tính (ví dụ `follow_friends_suggestion_popup` "Follow bạn bè của bạn") đã có dismisser trong `flows/benign_popup.py` nhưng chưa được nối vào `core/classifier.py` (`classify_tiktok_screen`).
- **Khắc phục:**
  1. Replay artifact UI XML ngoại tuyến để kiểm tra `flows.benign_popup.detect_<popup>(root)`.
  2. Nối nhánh popup đó vào `core/classifier.py` để phân loại chính xác thành `GENERIC_POPUP_SCREEN` (`manual-needed:popup`) kèm lý do cụ thể.
  3. Chạy focused test: `pytest python_runner/tests/test_classifier.py`.

## 2. Profile Switch Anchor Bounds vs Center Verification
- **Triệu chứng:** Máy mở Profile sau khi chuyển đổi tài khoản nhưng bị lỗi `profile username still mismatched after switch` hoặc tap nhầm vào `@username` thay vì dropdown switch.
- **Nguyên nhân:** Trong `flows/feed_swipe_smoke.py::_find_sticky_profile_header`, điều kiện lọc kiểm tra tọa độ tâm `anchor.center[1] <= 320`. Trên Samsung S7 (1080x1920), button tên hiển thị (display name) thật có bounds `[36, 280][444, 364]` với tâm `y = 322 > 320`, khiến anchor hợp lệ bị loại bỏ và fallback chọn nhầm link username phía dưới (`y ~ 392`).
- **Khắc phục:**
  1. Chuyển sang kiểm tra mép trên của bounds: `anchor.bounds is not None and anchor.bounds[1] <= 320`.
  2. Ưu tiên node `display_name_element` thật thay vì `display_name_anchor_element` (tránh FrameLayout rỗng).
  3. Chạy focused test: `pytest python_runner/tests/test_machine74_direct_feed_session.py`.

## 3. Samsung FOTA Occlusion Handling
- **Triệu chứng:** Máy Admin (ví dụ M261) bị kẹt ở popup hệ thống Samsung FOTA (`com.wssyncmldm`), làm TikTok mất focus liên tục và fail preflight.
- **Nguyên nhân:** `recover_systemui_occlusion()` chỉ kiểm tra `com.android.systemui`.
- **Khắc phục:**
  1. Thêm `com.wssyncmldm` vào `SYSTEM_OCCLUSION_PACKAGES` trong `flows/device_prepare.py`.
  2. Tự động gửi KEYEVENT 4 (BACK) khi phát hiện foreground package là `com.wssyncmldm`.
  3. Chạy focused test: `pytest python_runner/tests/test_device_prepare.py`.

## 4. Subprocess Window Invariant on Windows
- **Triệu chứng:** Test an toàn cronjob `test_guard_cronjob_safety.py` báo `[CONSOLE_WINDOW_BLOCKED]` và cướp focus của máy host.
- **Nguyên nhân:** Lệnh gọi `subprocess.run()` hoặc `Popen()` trong script thiếu cờ `creationflags=subprocess.CREATE_NO_WINDOW`.
- **Khắc phục:** Luôn luôn thêm `creationflags=subprocess.CREATE_NO_WINDOW` vào mọi lệnh gọi subprocess trên Windows.
