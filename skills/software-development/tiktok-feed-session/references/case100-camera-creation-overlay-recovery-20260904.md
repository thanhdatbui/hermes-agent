# Case 100: Camera Creation Overlay Detection & Dismissal Recovery (2026-09-04)

## Context & Incident
- **Machine / Account:** Máy 1 (serial `9885b64957334f5a46`, nick `ahmetsguthe17`).
- **Symptom:** Máy 1 dừng phiên feed session với alert `unexpected popup/dialog marker detected`. Hiện trường mở camera TikTok (màn hình chụp ảnh/quay video có nút ✕ ở góc trên bên trái, các nút CAMERA / TẠO, nút chụp tròn, Add sound...).

## Root Cause Analysis
1. **Classifier Scope Limitation (`core/classifier.py`):**
   - Logic cũ chỉ kiểm tra `bounds[1] >= 1000` với tập từ khóa hẹp (`{"10 phút", "60s", "15s", "văn bản", "10m", "templates", "photo", "camera"}`).
   - Khi màn hình camera có nút đóng ✕ ở góc trên bên trái (`y < 500`) hoặc xuất hiện các công cụ camera ("Add sound", "Filters", "Lật", "Hẹn giờ", "Tốc độ", "Effects", "Live", "Story"), classifier không gom nhóm được vào camera creation mà rơi vào generic popup `manual-needed:popup` ("unexpected popup/dialog marker detected").
2. **Dismiss Handler Sub-optimal Order (`flows/benign_popup_registry.py` & `flows/benign_popup.py`):**
   - `_dismiss_camera_creation` trong registry chỉ gửi `send_device_back_key(ctx)` mà không ưu tiên gọi `dismiss_camera_creation_screen` (tìm và tap chính xác nút ✕ đóng ở góc trên bên trái `y < 400`).
3. **Missing Overlay Handler in Navigation (`flows/calibrate_screens.py`):**
   - Trong `tap_navigation_target`, danh sách overlay được phép tự động dismiss trước khi thực hiện navigation tap bị thiếu `camera_creation_overlay`, dẫn đến việc không thể tự giải phóng màn hình camera trước khi bấm chuyển tab Profile / Home.

## Standard Fix Pattern
1. **Enrich Camera Screen Classifier (`core/classifier.py`):**
   - Quét toàn diện các modes (`"10 phút", "60s", "15s", "văn bản", "templates", "photo", "video", "live", "story", "tạo", "quay"`) và controls (`"lật", "hẹn giờ", "tốc độ", "bộ lọc", "thêm âm thanh", "hiệu ứng", "làm đẹp"`).
   - Nhận diện nút đóng ✕ ở `y < 500` (`{"✕", "×", "x", "đóng", "close"}` hoặc resource-id chứa `close_btn`/`btn_close`/`iv_close`).
   - Phân loại chính xác vào `GENERIC_POPUP_SCREEN` với `reasons=["TikTok camera/video creation screen detected via distinct creation mode elements"]`.
   - Giữ nguyên negative exclusion cho trang Profile để tránh false-positive.
2. **Two-Stage Camera Dismissal (`flows/benign_popup_registry.py`):**
   - `_dismiss_camera_creation` ưu tiên gọi `dismiss_camera_creation_screen(ctx)` để tìm và tap nút ✕ đóng ở góc trên `y < 400`.
   - Nếu không có nút ✕ hoặc tap thất bại, fallback an toàn sang `send_device_back_key(ctx)` với lý do `camera_creation_dismissed_via_back`.
3. **Pre-Navigation Overlay Allowlist (`flows/calibrate_screens.py`):**
   - Bổ sung `camera_creation_overlay` vào danh sách overlay được tự động dismiss trước khi tap target navigation trong `tap_navigation_target`.

## Verification Gate
- Unit tests: `pytest tests/test_classifier.py` (62 passed) & `pytest tests/test_benign_popup_registry.py` (159 passed).
- Live Canary Test Máy 1: `powershell.exe -ExecutionPolicy Bypass -File "D:\Taadaa\tiktok-luot nuoi acc\scripts\run-feed-session.ps1" -Machines 1 -Row 1 -RecoveryTestSwipes 2 -SkipAccountWorkbookSync -Run` ➔ `Status: success`, 2/2 swipes completed, exit code 0.
