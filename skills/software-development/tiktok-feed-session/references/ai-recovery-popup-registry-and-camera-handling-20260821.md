# AI Auto-Recovery, Centralized Benign Popup Registry & Camera Prevention (2026-08-21)

## 1. Tránh chạm nhầm nút Camera `[+]` ở đáy màn hình
- **Vị trí nút nguy hiểm:** Nút Tạo video / Camera của TikTok nằm chính giữa đáy thanh điều hướng (`x=540, y=1800+`). Mọi thao tác touch/vuốt từ vùng này đều có thể vô tình mở Camera.
- **Đóng Notification Shade (`_dismiss_notification_shade_if_open`):**
  - Tuyệt đối KHÔNG dùng gesture swipe up từ đáy (`Y >= 1700`).
  - Sử dụng duy nhất lệnh phi tiếp xúc `cmd statusbar collapse`.
  - Polling focus 4 lần x 0.5s: Nếu về `expected_package` -> return True; nếu lạc sang app khác -> fail-closed ngay lập tức.
- **Fallback click popup:**
  - Luôn tìm theo Element UI trong XML (`parse_xml`, `iter_elements`, `parse_bounds`).
  - Cấm hardcode tọa độ mù ở nửa dưới màn hình (`Y >= 1600`).

## 2. Đặc trị Camera / Overlay tại bước đối soát Hồ sơ (`_verify_profile_after_session`)
- Khi kết thúc phiên nuôi, script tap vào "Hồ sơ" để đối soát `@username`. Nếu vô tình lọt vào Camera overlay (do tap trúng nút `+` hoặc overlay chưa đóng):
  1. **Evidence Gate:** Không được kết luận `profile account mismatch` khi màn hình hoàn toàn thiếu `@username` (không quy kết nhầm thành sai tài khoản).
  2. **Tự động phục hồi:** Kích hoạt handler gửi `KEYCODE_BACK` để thoát Camera.
  3. **Tái điều hướng chuẩn:** Điều hướng lại Profile chuẩn qua `tap_navigation_target(CalibrationTarget('profile', ...))` và capture XML mới.
  4. **Fail-closed an toàn:** Nếu phục hồi thất bại, trả về `profile_verify_status = 'camera-recovery-failed'`, tuyệt đối không dùng XML Camera cũ để so sánh tài khoản.

## 3. Centralized `benign_popup_registry.py` & AI Auto-Recovery Deduplication
- **Registry tập trung:** Quản lý toàn bộ popup (Camera, Vị trí, Live overlay, Sound detail overlay, In-app browser, Ad overlay) trong `BENIGN_POPUP_REGISTRY` với độ ưu tiên (`priority`) và nguồn (`source='manual'`).
- **Bắt buộc gọi `register_popup_handler`:** Định nghĩa hàm `_detect_*` và `_dismiss_*` là chưa đủ; BẮT BUỘC phải đăng ký `register_popup_handler(RegistryEntry("<name>", priority, _detect_fn, _dismiss_fn, True, "manual"))`. Nếu thiếu dòng đăng ký, `find_matching_handler` duyệt `get_sorted_registry()` sẽ bỏ qua và popup không bao giờ được xử lý.
- **Xử lý Sound/Music Detail Overlay (`sound_detail_overlay`):** Nhận diện markers `"Sử dụng âm thanh"`, `"Use this sound"`, `"Thêm vào Nhật"`, `"Thêm vào Mục ưa thích"`. Thoát an toàn bằng `BACK` keyevent/actions để quay lại video feed.
- **Deduplication Check:** Khi AI Auto-Recovery phát hiện popup đã có trong Registry: Chỉ thực hiện lệnh ADB cứu máy lướt tiếp tại hiện trường, KHÔNG sinh code nối đuôi file (`code_patch = ""`).
- **AST Security Validation:** Kiểm tra và chặn các lệnh nguy hiểm (`os.system`, `subprocess`, `shutil.rmtree`, `eval`, `exec`).
- **Prompt Vision Client (`vision_client.py`):** Bắt buộc AI viết hàm parse Element UI từ XML, cấm hardcode tọa độ mù.
