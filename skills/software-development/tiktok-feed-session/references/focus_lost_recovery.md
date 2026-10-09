# TikTok Focus Lost & Post-Relaunch Recovery

## 1. Nguyên nhân mất Focus TikTok
- TikTok bị crash, kill hoặc rơi về Launcher (`com.sec.android.app.launcher`), SystemUI (`com.android.systemui`), hay app bên thứ 3.
- Dumpsys trả về focus package không thuộc TikTok (`com.ss.android.ugc.trill`, `com.zhiliaoapp.musically`, `com.ss.android.ugc.aweme`).
- False-positive focus loss do notification bar / status bar hoặc Samsung floating overlays tạm thời chiếm focus (`com.android.systemui`).

## 2. Phòng tránh False-Positive Focus Lost & Regex Nhận diện Cửa sổ
1. **Mở rộng Regex Focus Window (`FOCUS_RE`):**
   - Trên nhiều ROM Samsung/Android 9-11, dumpsys có thể không xuất hiện `mCurrentFocus` / `topResumedActivity` mà nằm ở `mFocusedWindow`, `mTopFullscreenOpaqueWindowState`, `mResumedActivity`, `mLastResumedActivity`.
   - Pattern regex cần bao quát: `(?:mCurrentFocus|mFocusedApp|topResumedActivity|mTopResumedActivity|mFocusedWindow|mTopFullscreenOpaqueWindowState|mResumedActivity|mLastResumedActivity)`.
2. **SystemUI Overlay vs In-App UI XML:**
   - Trong `core/safety.py`, nếu `focus_pkg` trả về `com.android.systemui` hoặc `None` nhưng UI XML khả dụng và không thuộc nhóm Google/GMS account packages, đồng bộ `focus_pkg = expected_package` để cho phép flow kiểm tra màn hình tiếp tục mà không báo ngộ nhận `TikTok focus lost`.
3. **Lọc SystemUI trong Classifier:**
   - Trong `_is_account_switcher_sheet` và các hàm phân loại subpage, loại trừ các element thuộc package `com.android.systemui` để tránh notification/status bar gây lệch nhận diện màn hình.

## 3. Chu trình phục hồi mất Focus (Launcher Recovery Ladder)
1. **Force-Stop & Relaunch TikTok:**
   - Dùng `_relaunch_and_poll_tiktok_focus` với độ trễ `POST_SWIPE_LAUNCHER_RECOVERY_WAIT_SECONDS` (6.0s).
   - Polling kiểm tra foreground package có thuộc TikTok hay không.

2. **Xử lý màn hình hậu Relaunch (Post-Relaunch Recapture):**
   - **Startup Ad / Splash Screen:** Sau khi mở lại app, TikTok thường hiển thị quảng cáo mở đầu. Phải gọi `_perform_startup_ad_skip` để bấm Bỏ qua và recapture lại.
   - **Benign Popups Draining:** `benign_drain_allowlist` phải bao quát tất cả popup lành tính thường gặp sau launch (`add-phone`, `security-check`, `quick-security`, `verify-email-prompt`, `link-email-prompt`, `notification-log`, `account-update-prompt`, ...) để `drain_known_popups` tự đóng popup về Feed.
   - **Loading Spinner:** Bounded loading retry để chờ app nạp xong video.

3. **Cập nhật trạng thái chuỗi kết quả (Results List):**
   - Khi `_recover_post_swipe_launcher_focus` phục hồi thành công `after` từ trạng thái `failed`/`manual-needed` sang `success`/`degraded`, bắt buộc cập nhật lại `results[-1] = after` và gọi `_store_partial_result` để không để lại row lỗi cũ trong session aggregate.

4. **Navigation Profile Preflight & Account Switcher Dismiss Fallback:**
   - Trong `_navigate_profile_for_preflight`, nếu `tap_navigation_target` thất bại do mất focus sang Launcher/SystemUI, tự động kích hoạt `_relaunch_and_poll_tiktok_focus` và thử tap lại Profile trước khi trả về lỗi.
   - Khi dismiss Account Switcher Sheet nếu không tìm thấy nút X / close element dạng UI node, gửi phím `BACK` (`keyevent 4`) để đóng bottom sheet về màn hình chính một cách an toàn.
