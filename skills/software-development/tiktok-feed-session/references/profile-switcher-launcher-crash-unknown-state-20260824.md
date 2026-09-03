# Profile Switcher Crash to Launcher and 'Unknown TikTok State' Misclassification

## Bối cảnh & Hiện tượng (2026-08-24)
Trên Farm Galaxy S7 (RAM 4GB, Android 8/OneUI), khi chạy flow `multi-machine-feed-session` qua cron (ví dụ batch `row-4-180049`), Telegram Farm Alerts báo lỗi:
- `🚨 [MÁY 5] DỪNG PHIÊN • Lý do: unknown TikTok state • Trạng thái: GIỮ HIỆN TRƯỜNG` kèm ảnh chụp màn hình Home/Launcher.

Cùng lúc đó, `[MÁY 37]` báo lỗi độc lập:
- `🚨 [MÁY 37] DỪNG PHIÊN • Lý do: required Android VPN is not connected: interface=tun0 ... ViChanger GET_IP failed after 3 retries: adb command timed out`.

## Phân tích chuỗi sự kiện Máy 5 (Root Cause)
1. **Preflight vào Hồ sơ:** Máy 5 mở TikTok thành công, điều hướng vào tab Hồ sơ (`profile_preflight_identity_guard`).
2. **Tap Switch Anchor:** Flow phát hiện nick hiện tại chưa đúng nick chỉ định (`hoangchau2078`), gọi `profile_preflight_switch_1` và tap anchor menu đổi tài khoản tại `[240, 159]`.
3. **App Crash về Launcher:** Khi drawer đổi tài khoản bung animation, TikTok trên S7 bị nghẽn tài nguyên/OOM crash văng thẳng về màn hình chính Android (`package="com.sec.android.app.launcher"`).
4. **Classifier kẹt ở Unknown State:**
   - Bước `profile_preflight_switcher_1_guard` capture màn hình + XML.
   - XML chứa toàn bộ node của Samsung Launcher (`com.sec.android.app.launcher`: Photos, Xóa bộ nhớ đệm, Danh bạ, Chrome, Gmail, TikTok...).
   - Thay vì nhận diện `focus_lost` / `launcher` để kích hoạt `_recover_launcher_focus` hoặc auto-relaunch, classifier tìm các marker TikTok, không thấy cái nào (`no known TikTok markers found`), gán nhãn `detected_screen="unknown"`.
   - Safety guard bắt `unknown TikTok state` -> gán `manual-needed` -> kích hoạt `preserve_blocker_screen` dừng phiên khẩn cấp.

## Bài học & Quy tắc xử lý
1. **Phân biệt hai lỗi độc lập:**
   - `ViChanger GET_IP failed`: Nghẽn ADB transport hoặc treo broadcast receiver ViChanger ở bước tiền kiểm VPN.
   - `unknown TikTok state` trên màn hình Home: Thực chất là **TikTok focus lost / Crash về Launcher** xảy ra ngay sau khi tap mở Switcher.
2. **Cải tiến Guard tại bước Account Switcher:**
   - Khi ở các bước preflight switcher (`profile_preflight_switcher_guard`), nếu `focused_package != tiktok_package` (hoặc XML thuộc `com.sec.android.app.launcher` / `com.android.systemui`), phải phân loại là `launcher_focus_loss` và kích hoạt recovery relaunch/switch thay vì để classifier rơi vào generic `unknown state`.
