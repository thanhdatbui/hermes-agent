# UIAutomator Helper App & LIVE Camera Surface Recovery

## 1. UIAutomator Helper App Stealing Foreground
- **Triệu chứng:** `OPEN_TIKTOK` hoặc `_wait_for_feed` liên tục không xác nhận được feed dù app đã launch, hoặc UI dump chứa package `com.github.uiautomator` thay vì `com.ss.android.ugc.trill`.
- **Nguyên nhân:** Quá trình chuẩn bị hoặc capture UI khiến app helper `com.github.uiautomator` (hoặc `io.appium.uiautomator2.server`) được đưa lên foreground của Android.
- **Xử lý tự động:**
  - Trong `bring_to_foreground` và `OPEN_TIKTOK`: Kiểm tra `dumpsys activity activities` / `mResumedActivity`. Nếu `com.github.uiautomator` đang ở foreground, gọi `am force-stop com.github.uiautomator` rồi đưa TikTok lên foreground (ưu tiên `com.ss.android.ugc.aweme.splash.SplashActivity`).
  - Trong `_wait_for_feed`: Nhận diện node `com.github.uiautomator` trong XML dump, tự động force-stop helper app và re-foreground TikTok.

## 2. Camera mở nhầm tab LIVE trong VIDEO_PICK
- **Triệu chứng:** Sau khi bấm nút Plus (`+`), màn hình chuyển sang giao diện camera nhưng không tìm thấy nút thumbnail `Tải lên` (`view_bg2`, `cwr`, `upload_hot_area`).
- **Nguyên nhân:** TikTok mở camera ở tab `LIVE` (chứa `Phát LIVE`, `Trung tâm LIVE`, hoặc tabs `xr4`: `ĐĂNG`, `TẠO`, `LIVE`). Ở chế độ LIVE không có nút tải ảnh/video từ thư viện.
- **Xử lý tự động:**
  - Nhận diện `_is_camera_surface_xml` bao gồm cả các marker của tab LIVE (`phát live`, `trung tâm live`, `text="LIVE"`, `text="live"`).
  - Khi phát hiện đang ở chế độ LIVE, tự động tap vào tab `ĐĂNG` hoặc `TẠO` (text `ĐĂNG` / `TẠO`) để chuyển camera về chế độ thông thường, từ đó thumbnail `Tải lên` xuất hiện.

## 3. Multi-Select Picker Button `Tiếp (1)`
- **Triệu chứng:** Khi chọn video trong picker, UI ở chế độ multi-select nên nút xác nhận hiển thị dạng `Tiếp (1)` hoặc `Next (1)` kèm số lượng, không khớp với exact match `text="Tiếp"`.
- **Xử lý tự động:**
  - Kiểm tra lần lượt `Tiếp (1)`, `Tiếp`, `Next (1)`, `Next`, `text_contains="Tiếp"`, `text_contains="Next"` và resource-ids `xip`, `pr7`.

## 4. Media Fingerprint Reservation Reuse on Target Retry
- **Triệu chứng:** Khi một canary run hoặc retry bị crash/timeout giữa chừng, lần chạy kế tiếp bị chặn bởi `[MEDIA_FINGERPRINT_PENDING] Exact media SHA-256 has unresolved ledger status=reserved`.
- **Xử lý tự động:**
  - Trong `MediaFingerprintLedger.reserve`: Nếu reservation có `status == "reserved"` nhưng cùng target `machine`, `target_account`, `video_number`, cho phép rebind/tái sử dụng reservation cho `run_id` mới thay vì bắt buộc chờ hết timeout `stale_after_seconds = 1800s`.
