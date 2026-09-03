# Benign Popup Registry & Camera Prevention Architecture (2026-08-21)

## 1. Centralized Benign Popup Registry (`benign_popup_registry.py`)
- **Nguyên lý:** Quản lý tập trung toàn bộ các popup, dialog, overlay thông thường (Camera recording overlay, Location permission prompt, In-app web browser, Interstitial ad overlay, Network error retry...) trong `BENIGN_POPUP_REGISTRY`.
- **Deduplication Check:** Khi AI Auto-Recovery phân tích màn hình gặp sự cố, hệ thống so khớp keyword/similarity với Registry. Nếu popup đã tồn tại handler:
  - Chỉ gửi lệnh giải phóng máy tại hiện trường qua ADB (như `KEYCODE_BACK` hoặc tap nút đóng).
  - Trả về `Code patch: ❌` và **tuyệt đối không sinh thêm hàm rác nối đuôi file**.
- **AST Security & Rollback An toàn:**
  - Kiểm tra AST allowlist (chặn `os.system`, `subprocess`, `shutil`, `eval`, `exec`).
  - Ghi file atomic dưới Mutex Lock.
  - Sửa lệnh `attempt_rollback()`: dùng `git revert <recorded_sha>` chính xác có mutex lock, không dùng `git revert HEAD` để tránh revert nhầm commit của máy khác.

## 2. Phòng tránh chạm nhầm nút Tạo Video / Camera `[+]` ở đáy TikTok
- **Notification shade dismissal (`_dismiss_notification_shade_if_open`):**
  - Tuyệt đối KHÔNG dùng gesture swipe từ đáy màn hình (`Y=1800+`) vì sẽ chạm nhầm vào nút `[+]` Camera ở đáy TikTok.
  - Sử dụng duy nhất lệnh non-touch `cmd statusbar collapse`.
  - Polling focus 4 lần x 0.5s: Nếu trở về TikTok (`expected_package`) -> thành công; nếu lạc sang app khác hoặc exception -> fail-closed ngay lập tức.
- **Tọa độ swipe/fallback an toàn:**
  - Điểm bắt đầu swipe / fallback tap phải đặt ở vùng an toàn `Y <= 1540`, tránh xa thanh điều hướng đáy (`Y=1800+`).
- **Profile verification camera recovery (`_verify_profile_after_session`):**
  - Khi đối soát username ở cuối phiên, nếu màn hình lọt vào Camera:
    1. Gửi `KEYCODE_BACK` thoát Camera.
    2. Điều hướng lại Hồ sơ qua `tap_navigation_target(profile)` có tự động scale tọa độ theo màn hình thiết bị.
    3. Hậu kiểm `not _detect_camera_creation(fresh_xml)` trước khi đối soát.
    4. Nếu không vào được Hồ sơ, fail-closed với `profile_verify_status = 'camera-recovery-failed'`, tuyệt đối không dùng XML camera để kết luận sai lệch tài khoản (`profile account mismatch`).
