# Profile Guard Launcher Focus Loss Recovery

## Context & Incident
Trên các thiết bị cấu hình thấp (như Samsung Galaxy S7), khi thực hiện tap vào switch anchor trên Profile (`profile_preflight_switch_1` / `tap_profile_switch_anchor`), animation mở drawer/bottom-sheet đổi tài khoản của TikTok có thể khiến app bị OOM / crash ngầm văng thẳng về Android Launcher (`com.sec.android.app.launcher`).

Ở bước kiểm tra kế tiếp (`profile_preflight_switcher_guard` hoặc `profile_preflight_identity_guard` gọi `_maybe_handle_profile_add_phone_guard`), capture attempt thu được cây XML của Launcher. Do không khớp với bất kỳ pattern popup hay feed nào, classifier gán nhãn `unknown TikTok state` và `ManualReasonGuard` kích hoạt dừng khẩn cấp với thông báo:
```text
🚨 [MÁY X] DỪNG PHIÊN
• Script: multi-machine-feed-session
• Lý do: unknown TikTok state
• Trạng thái: 🟡 GIỮ HIỆN TRƯỜNG ĐỂ HERMES AGENT XỬ LÝ
```
Ảnh hiện trường đính kèm là màn hình Home Android (với các icon Photos, Xóa bộ nhớ đệm, Danh bạ, Chrome, TikTok...).

## Solution & Implementation Pattern
Tích hợp kiểm tra `_is_launcher_focus_loss(ctx, row)` trực tiếp trong hàm điều phối guard cấp profile `_maybe_handle_profile_add_phone_guard`:

1. **Nhận diện mất focus:** Kiểm tra `_is_launcher_focus_loss(ctx, row)` (hỗ trợ đọc focus package từ cả top-level dict và nested `extra` dict).
2. **Khôi phục app:** Nếu `allow_dismiss=True`, gọi `force_stop_and_relaunch_tiktok(...)` với delay chờ sau launch `POST_SWIPE_LAUNCHER_RECOVERY_WAIT_SECONDS`.
3. **Tái điều hướng Profile:** Gọi `tap_navigation_target(ctx, _profile_target(), ...)` để đưa TikTok trở lại màn hình Hồ sơ.
4. **Xác thực nghiêm ngặt màn hình Profile sau khôi phục:** Chụp calibration attempt và bắt buộc kiểm tra `detected_screen == "profile"` (không chấp nhận các tab feed/home khác vì sẽ làm flow tiếp tục tap sai tọa độ switch anchor).
5. **Trả về kết quả:** Gán `popup_type="launcher_focus_loss"`, `popup_dismissed=True`, `status=SUCCESS`, `safety_status="ok"`, `detected="profile"` và trả về `("dismissed", row)`. Flow cha sẽ nhận trạng thái `dismissed` và an toàn thử tap lại switch anchor / verify identity thay vì fail-closed dừng phiên. Khi recovery thất bại hoặc không về được Profile, bắt buộc fail-closed trả về `("blocked", row)`.
