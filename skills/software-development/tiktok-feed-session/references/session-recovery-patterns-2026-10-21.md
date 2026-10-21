# Session Recovery Patterns & Fix Invariants (2026-10-21 Row 8 Incident)

## 1. Benign Popup Registry & Classifier Integration
- **Vấn đề:** Khi thêm detector hoặc dismisser cho popup lành tính mới (ví dụ: `follow_friends_suggestion_popup` "Follow bạn bè của bạn") trong `flows/benign_popup.py`, nếu không nối vào `core/classifier.py` (`classify_tiktok_screen`), guard preflight sẽ phân loại màn hình là `unknown` (confidence 0.0).
- **Hậu quả:** Runner dừng khẩn cấp với lỗi `unknown TikTok state` và đánh dấu `manual-needed`.
- **Quy tắc:**
  + Mọi benign popup được định nghĩa trong `flows/benign_popup.py` hoặc `benign_popup_registry.py` BẮT BUỘC phải được nối vào hàm `classify_tiktok_screen()` trong `core/classifier.py`.
  + Phải trả về `GENERIC_POPUP_SCREEN` (`manual-needed:popup`) kèm reason `known <popup_name> popup detected` để dismisser tự động đóng popup thay vì coi là màn hình lạ.
  + Luôn kiểm tra regression test: `pytest python_runner/tests/test_classifier.py`.

## 2. Profile Switch Anchor Bounds vs Center Verification
- **Vấn đề:** Trong `_find_sticky_profile_header()` (`flows/feed_swipe_smoke.py`), điều kiện kiểm tra vị trí header cũ dùng tọa độ tâm: `anchor.center[1] <= 320`.
- **Bẫy thực tế (Samsung S7 / màn hình 1080x1920):** Button hiển thị tên (display name) thật (ví dụ: `Anh Loan1`, bounds `[36, 280][444, 364]`) có tâm `y = 322`. Do `322 > 320`, anchor display name hợp lệ bị loại bỏ và flow rơi xuống username `@handle` phía dưới (`y ~ 392`), dẫn đến bấm nhầm vào nút copy link profile thay vì mở switcher.
- **Quy tắc:**
  + Thay vì kiểm tra tâm `center[1] <= 320`, BẮT BUỘC kiểm tra mép trên `bounds[1] <= 320` (`anchor.bounds is not None and anchor.bounds[1] <= 320`).
  + Ưu tiên node `display_name_element` thật trước `display_name_anchor_element` (tránh bốc nhầm FrameLayout rỗng).
  + Kiểm chứng: Replay trực tiếp trên UI XML artifact của máy lỗi và chạy `pytest python_runner/tests/test_machine74_direct_feed_session.py`.

## 3. System Occlusion & Samsung FOTA Handling
- **Vấn đề:** Màn hình bị popup hệ thống Samsung FOTA (`com.wssyncmldm`) đè focus khi mở TikTok. Lệnh broadcast `android.intent.action.CLOSE_SYSTEM_DIALOGS` không thể đóng popup cập nhật phần mềm này.
- **Quy tắc:**
  + Bổ sung `com.wssyncmldm` vào danh sách `SYSTEM_OCCLUSION_PACKAGES` trong `flows/device_prepare.py` cùng với `com.android.systemui`.
  + Gửi lệnh fallback `input keyevent 4` (BACK) khi phát hiện foreground package là `com.wssyncmldm` để đóng hộp thoại cập nhật và trả focus cho TikTok.
  + Kiểm chứng: `pytest python_runner/tests/test_device_prepare.py`.

## 4. Subprocess Console Window Invariant on Windows
- **Vấn đề:** Mọi lệnh gọi `subprocess.run()`, `subprocess.Popen()` trong các runner/cron scripts trên Windows (như `do_rename_canonical_runner.py`) nếu thiếu cờ `creationflags=subprocess.CREATE_NO_WINDOW` (hoặc `0x08000000`) sẽ làm bật cửa sổ CMD đen cướp focus của máy tính và bị chặn bởi guard an toàn cronjob.
- **Quy tắc:** Luôn luôn đính kèm `creationflags=subprocess.CREATE_NO_WINDOW` cho tất cả subprocess con trên Windows.
