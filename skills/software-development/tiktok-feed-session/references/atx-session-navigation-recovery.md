# Phục Hồi ATX_SESSION_UNAVAILABLE Trong Navigation (Case 108 & Case 109)

## 1. Triệu chứng & Hiện trường
- Khi điều hướng tab (Profile preflight hoặc Home navigation `before_swipe`), `tap_navigation_target` trả về lỗi:
  `ATX_SESSION_UNAVAILABLE: ATX session UI capture failed after retry and reset` hoặc `UI_DUMP_FAILED`.
- App TikTok vẫn đang chạy trên màn hình thiết bị (`get_focused_activity(ctx)` trả về package TikTok), nhưng daemon `atx-agent` / uiautomator stub bị disconnect hoặc crash ngầm.

## 2. Điểm Kẹt Cần Khắc Phục
- **Case 108:** Tại `_navigate_profile_for_preflight`, trước đây chỉ bắt `is_launcher` để relaunch. Nếu app vẫn ở TikTok foreground nhưng ATX rớt kết nối, script vội vã báo `manual-needed` và dừng phiên.
- **Case 109:** Tại `_feed_session_flow` (`home_navigation`), sau `_maybe_recover_navigation_from_add_phone`, nếu `home_navigation.ok` là `False` do lỗi ATX session trong khi TikTok vẫn ở foreground, script dừng ngay tại `before_swipe` thay vì tự phục hồi daemon.

## 3. Pattern Chuẩn Phục Hồi ATX Session Khi TikTok Foreground
```python
if not navigation.ok:
    current_focus = {}
    try:
        current_focus = get_focused_activity(ctx)
        if not isinstance(current_focus, dict):
            current_focus = {}
    except Exception:
        current_focus = {}
    current_pkg = str(current_focus.get("package") or "")
    package_name = str(ctx.config.get("tiktok_package", "com.ss.android.ugc.trill"))
    tiktok_pkgs = {package_name, "com.ss.android.ugc.trill", "com.zhiliaoapp.musically", "com.ss.android.ugc.aweme"}

    nav_status_upper = str(navigation.status or "").upper()
    nav_reason_lower = str(navigation.reason or "").lower()
    is_atx_failure = (
        nav_status_upper in {"ATX_SESSION_UNAVAILABLE", "UI_DUMP_FAILED"}
        or "atx_session_unavailable" in nav_reason_lower
        or "atx session" in nav_reason_lower
        or "uidumperror" in nav_reason_lower
        or "ui capture failed" in nav_reason_lower
    )
    if current_pkg in tiktok_pkgs and is_atx_failure:
        ctx.logger.log(
            device_id=ctx.device_id,
            account=ctx.account,
            step=f"{artifact_prefix}/{step_name}",
            action=f"{step_name}_atx_recovery",
            result="retry",
            extra={"reason": navigation.reason, "status": navigation.status, "focus_package": current_pkg},
        )
        try:
            from automation_core.persistent_ui import reset_atx_agent
            reset_atx_agent(ctx.adb, timeout=15)
            time.sleep(1.0)
        except Exception as reset_err:
            ctx.logger.log(
                device_id=ctx.device_id,
                account=ctx.account,
                step=f"{artifact_prefix}/{step_name}",
                action=f"{step_name}_atx_reset_failed",
                result="warning",
                error=str(reset_err),
            )
        # Retry navigation 1 lần an toàn
        navigation = tap_navigation_target(
            ctx,
            target,
            current_top_tab=current_top_tab,
            artifact_prefix=artifact_prefix,
            log_prefix=artifact_prefix,
        )
```

## 4. Các Rào Chắn An Toàn (Safety Guards) Bắt Buộc
1. **Tuân thủ Case 105 (Back Guard):** TUYỆT ĐỐI KHÔNG gửi `KEYCODE_BACK` (`input keyevent 4`) khi app đang ở Home Feed hoặc Launcher để tránh làm văng ứng dụng ra màn hình chính.
2. **Tuân thủ Case 103 (No Monkey / No Occlusion):** `reset_atx_agent` phải khởi động stub qua HTTP endpoint `POST /uiautomator`, CẤM dùng `monkey -p com.github.uiautomator 1` gây bung activity xoay ngang.
3. **Giới hạn số lần retry:** Chỉ retry tối đa 1 lần với bounded timeout (15s). Nếu sau khi reset ATX mà capture vẫn fail, bảo toàn nguyên vẹn `UIDumpError` gốc, không được nuốt exception thành `not-found`.
