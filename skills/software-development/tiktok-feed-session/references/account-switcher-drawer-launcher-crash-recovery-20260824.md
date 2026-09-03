# Account Switcher Drawer Launcher Crash & Recovery

## Bối cảnh & Hiện tượng
Trên các thiết bị Android cấu hình RAM thấp (như Samsung Galaxy S7), khi thực hiện thao tác tap vào nút mở menu đổi tài khoản (Profile account switcher drawer), animation trượt của bottom sheet hoặc tải danh sách tài khoản có thể làm TikTok crash ngầm và văng focus về màn hình chính Android (`com.sec.android.app.launcher` hoặc `com.android.systemui`).

Tại chốt kiểm tra `profile_preflight_switcher_guard` (hoặc `_maybe_handle_profile_add_phone_guard`), việc đọc UI XML trên màn hình Launcher sẽ không tìm thấy bất kỳ marker TikTok hợp lệ nào, dẫn đến việc classifier gán nhãn `unknown TikTok state` và kích hoạt cơ chế `GIỮ HIỆN TRƯỜNG`, làm dừng phiên và gửi cảnh báo về Telegram.

## Phân tích Call Chain & Điểm mù (Coverage Gap)
Trước bản vá, cơ chế `force_stop_and_relaunch_tiktok` chỉ bao phủ 3 vị trí:
1. `_maybe_prepare_after_launcher_baseline` (Startup / Baseline khi vừa mở app).
2. `_recover_post_swipe_launcher_focus` (Sau mỗi nhịp vuốt video feed).
3. `_maybe_recover_navigation_from_add_phone` (Khi tap chuyển đổi giữa các tab chính).

Tại nhánh Profile Guard (`_maybe_handle_profile_add_phone_guard`), hệ thống chỉ kiểm tra các popup thông thường (Add phone, Quick security, Verify email, Google account...) mà thiếu nhánh nhận diện `_is_launcher_focus_loss`.

## Giải pháp & Hợp đồng Recovery
Tại `_maybe_handle_profile_add_phone_guard`:
1. Kiểm tra `_is_launcher_focus_loss(ctx, row)`.
2. Nếu `allow_dismiss=True`:
   - Gọi `force_stop_and_relaunch_tiktok(ctx, package_name=package_name, after_launch_delay_seconds=POST_SWIPE_LAUNCHER_RECOVERY_WAIT_SECONDS, raise_on_result_failure=False)`.
   - Khi launch thành công, điều hướng lại về tab Hồ sơ qua `tap_navigation_target(ctx, _profile_target(), ...)`.
   - Capture lại UI attempt sau khi relaunch; nếu màn hình sau đó là màn hình TikTok hợp lệ (`profile`, `friends`, `following`, `for-you`, `home`), gán `row["popup_type"] = "launcher_focus_loss"`, `row["popup_dismissed"] = True` và trả về `("dismissed", row)`.
   - Flow gọi caller sẽ tự động retry mở lại account switcher mà không bị fail-closed oan.
3. Nếu recovery thất bại hoặc không được phép dismiss: giữ trạng thái fail-closed và ghi nhận `popup_type="launcher_focus_loss"`.
