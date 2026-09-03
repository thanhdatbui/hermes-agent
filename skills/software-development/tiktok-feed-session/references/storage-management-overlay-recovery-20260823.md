# Phục hồi Màn hình "Giải phóng dung lượng" (Storage Management Overlay Recovery) (2026-08-23)

## 1. Hiện tượng & Triệu chứng
- **Alert Telegram:** `🚨 [MÁY XX] DỪNG PHIÊN`
- **Script:** `multi-machine-feed-session` / `feed-session-smoke`
- **Lý do báo lỗi:** `unexpected popup/dialog marker detected` (phân loại `manual-needed:popup`).
- **Hình ảnh hiện trường:** Màn hình *"Giải phóng dung lượng"* (*Free up space* / `snssdk1180://clean_cache`), hiển thị dung lượng Dữ liệu TikTok, Bộ nhớ đệm (Cache) kèm các nút *"Xóa"*.

## 2. Nguyên nhân Gốc rễ
1. **Lịch dọn cache cuối ngày:** Cron `end-of-day-clear-tiktok-cache` mở màn hình này qua Intent Deep Link `snssdk1180://clean_cache`.
2. **Task Stack / Recent Apps Lag:**
   - Trong khâu `prepare_tiktok_for_smoke`, nếu thao tác `close_all_apps_start` (bấm Recent Apps `187`) bị trễ hoặc không tìm thấy nút "Đóng tất cả", app TikTok ở màn hình Cài đặt có thể chưa bị đóng triệt để.
   - Khi launch lại TikTok, app resume thẳng vào sub-activity `TikTokHostActivity` (Giải phóng dung lượng) thay vì màn hình Trang chủ/Feed.
3. **Classifier Safety Boundary:**
   - Giao diện Cài đặt không có các tab điều hướng Feed (*"Trang chủ"*, *"Đề xuất"*, *"Bạn bè"*) và chứa các nút action `Xóa` / `android:id/button` $\rightarrow$ Classifier nhận diện `manual-needed:popup` để bảo vệ an toàn (tránh vuốt hoặc tap nhầm vào nút xóa dữ liệu).

## 3. Giải pháp Tự động Phục hồi (Benign Popup Registry)
- Đăng ký handler `storage_management_overlay` trong `python_runner/flows/benign_popup_registry.py`:
  - **Priority:** `81` (sau `camera_creation_overlay` và `follow_friends_suggestion_popup`).
  - **Detector (`_detect_storage_management`):**
    - Kiểm tra từ khóa tiêu đề: `Giải phóng dung lượng`, `Free up space`, `Dữ liệu TikTok`.
    - Kiểm tra từ khóa nội dung: `Bộ nhớ đệm`, `Tải về`, `Clear cache`.
  - **Dismisser (`_dismiss_storage_management`):**
    - Gửi phím `KEYCODE_BACK` (`4`) hoặc `ctx.actions.back()` để thoát khỏi sub-activity Cài đặt và quay trở lại Trang chủ/Feed an toàn.
  - **Tích hợp:** Tự động kích hoạt trong flow `dismiss_any_popup` khi `allow_benign_popup_dismiss=True` (mặc định bật trong `multi-machine-feed-session`).

## 4. Test Verification
- Đã bổ sung unit tests trong `python_runner/tests/test_benign_popup_registry.py`:
  - `test_find_matching_storage_management_handler`
  - `test_dismiss_any_popup_triggers_storage_management`
- Chạy kiểm tra toàn bộ suite liên quan:
  ```bash
  python -B -m pytest -q -p no:cacheprovider python_runner/tests/test_benign_popup_registry.py python_runner/tests/test_benign_popup.py
  ```
