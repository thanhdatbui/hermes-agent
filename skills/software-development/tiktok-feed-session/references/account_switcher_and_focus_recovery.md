# Account Switcher & Focus Modal Recovery Guide

## 1. SystemUI Notification False Positives in Account Switcher Detection
- **Triệu chứng:** TikTok mở BottomSheet "Chuyển đổi tài khoản", nhưng classifier nhận diện nhầm thành `manual-needed:login` hoặc không nhận diện được switcher sheet.
- **Root cause:** Thanh trạng thái Android / SystemUI chứa thông báo (ví dụ: *"Thông báo của Dịch vụ Google Play: Yêu cầu đăng nhập"*). Hàm `_is_account_switcher_sheet` duyệt qua tất cả element của root dump (gồm cả SystemUI) và quét `blocker_terms` ("đăng nhập", "login", v.v.), dẫn đến `has_blocker = True`.
- **Cách xử lý chuẩn:**
  - Trong `_is_account_switcher_sheet` (`core/classifier.py`), filter bỏ triệt để các node có `package == 'com.android.systemui'` hoặc `resource-id` bắt đầu bằng `'com.android.systemui:'`.

## 2. Modal / BottomSheet Focus Unavailable in `safety_check`
- **Triệu chứng:** Khi mở modal/sheet trong TikTok, `dumpsys window` trả về package rỗng hoặc `com.android.systemui`, khiến `safety_check` báo lỗi `focused package unavailable`.
- **Root cause:**
  1. `safety_check` chỉ fallback `focus_pkg = expected` khi màn hình phát hiện nằm trong `KNOWN_TIKTOK_SCREENS` hoặc `MANUAL_SCREEN_REASONS`. Một số màn hình đặc thù (`manual-needed:account-update-prompt`, `manual-needed:vichanger-lsposed`, `manual-needed:usb-debugging`, `packageinstaller/system-dialog`) bị thiếu trong enum `MANUAL_SCREEN_REASONS`.
  2. `FOCUS_RE` trong `flows/observe.py` và `core/ui_capture.py` thiếu các trường dumpsys bổ trợ của Samsung như `mFocusedWindow`, `mTopFullscreenOpaqueWindowState`, `mResumedActivity`, `mLastResumedActivity`.
- **Cách xử lý chuẩn:**
  - Mở rộng `MANUAL_SCREEN_REASONS` và cho phép fallback an toàn cho tất cả màn hình dạng `manual-needed:*` khi XML khả dụng và không thuộc Google/account packages.
  - Cập nhật `FOCUS_RE` bao quát các khóa cửa sổ focus của Samsung Android.
