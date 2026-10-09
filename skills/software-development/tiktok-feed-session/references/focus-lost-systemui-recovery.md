# Xử lý Alert TikTok Focus Lost & SystemUI Overlay Recovery

## 1. Hiện tượng & Triệu chứng
- **Alert:** `TikTok focus lost` hoặc `Status: failed` / `Status: manual-needed` ngay tại bước baseline, before_swipe, hoặc trong vòng lặp vuốt feed.
- **Triệu chứng ngầm:**
  - Dumpsys trả về `mCurrentFocus=Window{... StatusBar}` (package `com.android.systemui`), nhưng `mFocusedApp` vẫn là TikTok (`com.ss.android.ugc.trill` hoặc `SplashActivity`).
  - Thiết bị dùng package TikTok biến thể (`com.zhiliaoapp.musically`, `com.ss.android.ugc.aweme`) lệch với config mặc định `com.ss.android.ugc.trill`.
  - Màn hình hiển thị popup hoặc dialog nội bộ TikTok trong khi thanh trạng thái/SystemUI đang hoạt động.

## 2. Các điểm chốt trong Codebase

### A. Parser Focus (`python_runner/flows/observe.py`)
- **Nguyên tắc:** Dùng `FOCUS_RE.findall(output)` quét toàn bộ các cặp `(package, activity)` trong output dumpsys.
- **Thứ tự ưu tiên:**
  1. Nếu xuất hiện bất kỳ package TikTok nào (`com.ss.android.ugc.trill`, `com.zhiliaoapp.musically`, `com.ss.android.ugc.aweme`) -> Trả về package TikTok đó ngay lập tức (bỏ qua `com.android.systemui`).
  2. Nếu không có TikTok, ưu tiên package không phải `com.android.systemui`.
  3. Cuối cùng mới fallback về match đầu tiên.

### B. Safety Check & Popup Recovery (`python_runner/core/safety.py`)
- **Tập package TikTok chuẩn:**
  ```python
  KNOWN_TIKTOK_PACKAGES = {
      DEFAULT_TIKTOK_PACKAGE,
      "com.ss.android.ugc.trill",
      "com.zhiliaoapp.musically",
      "com.ss.android.ugc.aweme",
  }
  SYSTEM_OVERLAY_PACKAGES = {
      "com.android.systemui",
      "android",
      "com.sec.android.inputmethod",
      "com.samsung.android.app.cocktailbarservice",
  }
  ```
- **Xử lý Package Biến thể:** Nếu cả `expected` và `focus_pkg` đều nằm trong `KNOWN_TIKTOK_PACKAGES` -> chuẩn hóa `focus_pkg = expected`.
- **Bảo toàn Popup Dưới System Overlay:** Khi `focus_pkg != expected` nhưng `xml_available` là `True` và `detected` là màn hình TikTok hoặc popup đã định danh (`is_known_tiktok_screen`):
  -> Gán `focus_pkg = expected` để flow chuyển tiếp sang bộ dismiss popup thay vì fail cứng với `"TikTok focus lost"`.

### C. Feed Swipe Flow Checks (`python_runner/flows/feed_swipe_smoke.py`)
- Tất cả các hàm kiểm tra focus khởi động và vuốt nhanh:
  - `_has_tiktok_startup_focus`
  - `_is_splash_launch_focus`
  - `_keyboard_cleanup_candidate`
  - `_splash_slow_capture_retry`
  - `capture_coordinate_swipe_fallback`
  - `evaluate_screen_attempt`
  - `fast_swipe_focus_check`
  Đều phải kiểm tra theo set `tiktok_pkgs = {expected_package, "com.ss.android.ugc.trill", "com.zhiliaoapp.musically", "com.ss.android.ugc.aweme"}` thay vì kiểm tra đơn lẻ `!= expected_package`.

## 3. Quy trình Kiểm thử & Xử lý Khóa Máy (Device Lock)
- **Pytest:** Chạy các test suite liên quan trước khi kết luận:
  `pytest python_runner/tests/test_safety.py python_runner/tests/test_observe.py python_runner/tests/test_feed_swipe_smoke.py`
- **Xử lý Stale Lock:** Nếu canary test báo `skipped-device-locked` do process trước chưa giải phóng:
  Kiểm tra và xóa lock file tại `C:\Users\Kibe\.codex\device-locks\machine_<N>.lock.json` sau khi tiến trình cũ đã dừng.
