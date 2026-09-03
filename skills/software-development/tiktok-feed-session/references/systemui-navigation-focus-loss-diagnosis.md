# Chẩn đoán & Xử lý lỗi TikTok Focus Lost (SystemUI Navigation Tap)

## Ngữ cảnh & Triệu chứng
* **Thông báo cảnh báo:**
  `profile verification navigation-failed: TikTok focus lost after navigation tap: com.android.systemui`
* **Vị trí code:** `python_runner/flows/calibrate_screens.py` -> `tap_navigation_target`
* **Cơ chế:** Khi thực hiện `input tap` để điều hướng (ví dụ: chuyển sang tab Profile/Home để verify danh tính sau phiên lướt), trên các thiết bị Android Samsung có thanh điều hướng ảo/gesture bar nằm sát đáy màn hình (`y >= 1850` trên màn 1080x1920), cú chạm có thể chạm trúng thanh điều hướng hệ thống hoặc kích hoạt đa nhiệm khiến `com.android.systemui` (Recent Apps) nhảy lên foreground. Hàm `verify_tiktok_focus_after_navigation` phát hiện `post_package != expected_package` và kích hoạt dừng phiên để tránh đọc sai UI XML của SystemUI thành lỗi identity/nick.

## Quy trình kiểm tra & Xử lý hiện trường
1. **Kiểm tra trạng thái máy qua ADB:**
   * Lấy serial máy từ workbook / config (`Tik1.xlsx` / `config-machine-N.yaml`).
   * Kiểm tra focus thực tế: `adb -s <serial> shell dumpsys window | grep -E "mCurrentFocus|mFocusedApp"`
   * Chụp screencap kiểm tra màn hình hiện tại: `adb -s <serial> exec-out screencap -p > screen.png`
2. **Đánh giá tình trạng:**
   * Nếu TikTok đã tự động trở lại foreground (hoặc khi mở lại app vẫn ở feed bình thường): Thiết bị hoàn toàn bình thường, không bị văng nick hay hỏng session.
   * Đây là lỗi điều hướng thoáng qua (transient navigation focus loss), không cần can thiệp dữ liệu tài khoản.
3. **Báo cáo & Khởi động lại:**
   * Báo cáo rõ nguyên nhân do SystemUI chiếm focus lúc tap điều hướng.
   * Xác nhận tình trạng màn hình hiện tại của máy và tiến hành resume/re-run phiên feed.

## Hướng vá lỗi code triệt để (Code Fix Architecture - Đã triển khai)
1. **Auto-recovery Focus trong `tap_navigation_target` (`python_runner/flows/calibrate_screens.py`):**
   * Khi phát hiện `post_package in {"com.android.systemui", "com.sec.android.app.launcher", "com.google.android.apps.nexuslauncher"}`, hệ thống không fail ngay mà:
     * Log action `recover_tiktok_focus_after_systemui_tap` với status `retry`.
     * Gửi phím `KEYCODE_BACK` (`input keyevent 4`) để thoát Recent Apps / Launcher trở lại app.
     * Chờ 1.2s và kiểm tra lại `get_focused_activity(ctx)`.
     * Nếu `retry_pkg == expected_package` ➔ đánh dấu `recovered_focus = True`, gán lại `post_focus / post_package`, log `success` và tiếp tục luồng đối soát bình thường.
     * Nếu sau 1 lần retry vẫn kẹt ở SystemUI/Launcher ➔ mới fail-closed qua `safety_check` và raise cảnh báo an toàn.
2. **Unit Test Verification (`python_runner/tests/test_calibrate_screens.py`):**
   * Bổ sung test `test_navigation_recovers_focus_when_recent_apps_dismissed_by_back_key`: mock chuỗi focus `[TikTok, SystemUI, TikTok]` và xác nhận lệnh `keyevent 4` được gọi, kết quả trả về `ok=True`, status `pass`.
   * Giữ vững test fail-closed `test_navigation_fails_closed_when_focus_moves_to_recent_apps_after_tap` khi chuỗi focus `[TikTok, SystemUI, SystemUI]` không tự hồi phục.
