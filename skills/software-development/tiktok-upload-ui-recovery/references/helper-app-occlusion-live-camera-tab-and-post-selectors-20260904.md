# Helper App Occlusion, LIVE Camera Mode Recovery & Extended Post Selectors (2026-09-04)

## 1. Helper App Occlusion (`com.github.uiautomator` / `io.appium.uiautomator2`)
### Triệu chứng:
- Khi chạy workflow TikTok (Upload / Feed / Switcher), tiến trình UIAutomator helper app hoặc stub bị bung lên foreground chiếm màn hình.
- `_wait_for_feed`, `OPEN_TIKTOK`, hoặc `ACCOUNT_SWITCHER` chờ mãi không thấy root surface TikTok hoặc báo `package is not in foreground`.
### Xử lý chuẩn trong Codebase:
- Trong `OPEN_TIKTOK`, `WAIT_FEED`, `ACCOUNT_SWITCHER`: Kiểm tra nếu `focused_pkg` hoặc chuỗi XML chứa `com.github.uiautomator`, `io.appium.uiautomator2`, `io.appium.uiautomator2.server`.
- Lập tức thực hiện:
  1. `am force-stop com.github.uiautomator`
  2. `am force-stop io.appium.uiautomator2.server`
  3. Gọi `bring_to_foreground("com.ss.android.ugc.trill")` và sleep 1-2s để trả quyền điều khiển cho TikTok.

## 2. Camera mở nhầm chế độ LIVE Tab
### Triệu chứng:
- Khi bấm nút `+` (Create/Plus), TikTok mở camera ở tab `LIVE` / `Phát LIVE` thay vì tab quay video / upload thông thường.
- XML không xuất hiện thumbnail thư viện ảnh `view_bg2` hoặc `upload_hot_area` dẫn đến timeout `VIDEO_PICK_CREATE_ENTRY_UNCONFIRMED`.
### Xử lý:
- Trong `_open_camera_gallery_entry` và `_handle_video_pick`: Quét XML tìm các marker `phát live`, `trung tâm live`, `text="live"`.
- Nếu phát hiện chế độ LIVE: tap chuyển ngay sang tab `"ĐĂNG"` hoặc `"TẠO"` (`adapter._tap_if_found(xml, text="ĐĂNG") or adapter._tap_if_found(xml, text="TẠO")`), chờ 2s rồi dump lại XML để lấy thumbnail gallery.

## 3. Mở rộng Selector nút Post / Đăng trên Final Composer
### Triệu chứng:
- TikTok cập nhật layout composer mới, các resource-id cũ (`sh8`, `shd`) bị đổi hoặc ẩn dưới các ID mới như `sox`, `soz`, `sp7`, `rbp`, `post_action`, `post_button`.
### Xử lý:
- Duyệt qua toàn bộ danh sách ID ưu tiên: `("sh8", "shd", "sox", "soz", "sp7", "rbp", "post_action", "post_button")` trước khi fallback sang tìm kiếm theo text `"Đăng"` / `"Post"`.

## 4. Idempotency Post Receipt Scoping & Auto-Advance
### Nguyên tắc:
- Mọi post receipt phải được scope theo `machine` VÀ `target_account` (`machine_{machine}_account_{target_account}_video_{video_number}.json`).
- Khi video đã được xác nhận đăng thành công trong ledger (`verified_success`), cơ chế `_auto_advance_verified_videos` phải tự động tăng `video_number` và cập nhật lại đường dẫn file video thật (`video_path = resolve_video_path(...)`) cũng như đồng bộ cursor trên workbook.
