# UIAutomator Stub Monkey Relaunch vs TikTok Focus Loss (2026-08-23)

## Hiện tượng & Dấu hiệu
- **Telegram Alert:** `TikTok focus lost; swipe recovery (2 swipes) still stuck` trên `multi-machine-feed-session`.
- **Ảnh đính kèm hiện trường:** Màn hình hiển thị app `UIAutomator` (`com.github.uiautomator.MainActivity`) với grid phím tắt tiếng Trung (`开发者选项`, `无障碍服务`, `关闭所有服务`, `开启悬浮窗`, v.v.).
- **Dumpsys Evidence:**
  - `mCurrentFocus`: `com.github.uiautomator/com.github.uiautomator.MainActivity`
  - `com.ss.android.ugc.trill` vẫn đang chạy nền (`pid` còn sống, task stack nằm dưới).

## Chuỗi nguyên nhân (Root Cause Cascade)
1. **ATX Capture Retry/Reset:** Khi ATX agent trên thiết bị phản hồi chậm hoặc fail 3 lần trong `capture_required_ui_result()`, helper gọi `reset_atx_agent(adb)` từ `automation-core`.
2. **Monkey Stub Warmup:** Trong `reset_atx_agent()`:
   ```python
   adb.shell(["monkey", "-p", "com.github.uiautomator", "1"], timeout=timeout, check=False)
   ```
   Lệnh `monkey` gửi event trực tiếp đến package `com.github.uiautomator`, kích hoạt `com.github.uiautomator.MainActivity` lên foreground.
3. **Mất Foreground TikTok:** `com.github.uiautomator.MainActivity` đè lên giao diện TikTok (`com.ss.android.ugc.trill`).
4. **Swipe Recovery Failure:** Flow feed rơi vào `swipe_recovery_on_stuck()` và thử vuốt 2 lần (`input swipe 540 1600 540 400 300`). Việc vuốt trên app UIAutomator không đưa TikTok trở lại foreground, dẫn đến trigger dừng phiên với lý do `swipe recovery (2 swipes) still stuck`.

## Hướng xử lý & Phòng ngừa
1. **Tránh để UIAutomator chiếm Focus:** Khi reset/warmup UiAutomator stub trong `reset_atx_agent`, không nên để Activity `com.github.uiautomator.MainActivity` ở lại foreground lâu hoặc cần re-focus/bring-to-front TikTok (`am start -n com.ss.android.ugc.trill/com.ss.android.ugc.aweme.splash.SplashActivity` hoặc switch task) ngay sau khi khởi động stub.
2. **Phát hiện 3rd-party / UIAutomator Foreground trong Focus Lost Recovery:** Nếu phát hiện foreground bị chiếm bởi `com.github.uiautomator` hoặc launcher, flow recovery cần re-launch / re-focus package TikTok thay vì chỉ vuốt màn hình (vì vuốt không có tác dụng đổi app).
3. **Tuân thủ STOP GATE:** Khi máy dừng hiện trường ở màn UIAutomator, giữ nguyên hiện trường phục vụ triage theo đúng policy.
