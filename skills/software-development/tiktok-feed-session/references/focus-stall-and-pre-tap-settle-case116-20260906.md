# Case 116 (2026-09-06): Khắc Phục Lỗi Stall 5 Phút Trong get_focused_activity & Bổ Sung Pre-Tap Focus Settle Retry (Sự Cố Máy 40 - Nick jxlmiaxr6gt)

## 1. Hiện tượng & Triệu chứng lỗi thực tế
- **Alert**: `[FARM ALERT: MÁY 40] DỪNG PHIÊN`
- **Quy trình**: Nuôi Acc / Lướt Feed (`tiktok-luot nuoi acc`)
- **Nick**: `jxlmiaxr6gt` | Serial: `ce0418244d10342502`
- **Triệu chứng**: `run plan max_duration_seconds exceeded before capture profile_preflight_switch_anchor_2_pre_tap_guard attempt 1`
- **Thời gian ngâm**: Vượt quá trần deadline phiên (2100s) khi thực hiện profile preflight và account switcher.

---

## 2. Nguyên nhân cốt lõi (Root Cause)

### A. Stall 5 phút trong `get_focused_activity` (`flows/observe.py`)
- `get_focused_activity` gọi `capture_ui_xml(ctx.adb, timeout=15, ...)` không kèm các lightweight keys.
- Khi ATX session gặp trục trặc tạm thời hoặc độ trễ phản hồi, `capture_ui_xml` rơi xuống `dump_current_ui` -> `_dump_current_ui_unlocked`.
- Tại đây, hệ thống kích hoạt toàn bộ chuỗi recovery ladder cũ của automation-core: shell `uiautomator dump` attempt 1, 2, `uiautomator_stale_process_cleanup`, app relaunch x3 với monkey, và reboot.
- Quá trình này tiêu tốn 300+ giây (hơn 5 phút) cho **MỖI LẦN GỌI** `get_focused_activity`.
- Với nhiều lần kiểm tra focus liên tiếp trong profile preflight, tổng thời gian nhanh chóng vượt trần `max_duration_seconds` (2100s).

### B. Mất focus tạm thời (WindowManager Animation) Trước Navigation Tap
- Sau khi đổi tài khoản hoặc sau cú tap switcher, WindowManager trên Samsung S7 chuyển cảnh làm `get_focused_activity` trả về `{"package": None, "activity": None}`.
- Trong `tap_navigation_target` (`flows/calibrate_screens.py`), hàm chỉ kiểm tra focus 1 lần duy nhất trước khi tap. Khi `focus.get("package")` là None, `safety_check` đánh giá `SAFETY_FAILED` với lý do `"focused package unavailable"` và lập tức trả về `NavigationResult(False, 'fail', 'focused package unavailable')`.
- Thiếu cơ chế pre-tap settle retry khiến thao tác điều hướng bị fail-closed oan uổng dù TikTok vẫn đang ở foreground.

### C. Relaunch Vội Vã Khi Gặp 'Package Unavailable'
- Trong `_maybe_recover_navigation_from_add_phone` (`flows/feed_swipe_smoke.py`), khi gặp lý do `"package unavailable"`, code cũ nhảy ngay vào nhánh `_is_launcher_focus_loss` và gọi `force_stop_and_relaunch_tiktok`.
- Việc force-stop TikTok vừa mới load xong tài khoản khiến app bị kill, mất trạng thái đang mở, và tốn thêm 20-30s khởi động lại từ đầu.

---

## 3. Giải pháp chuẩn (Case 116 Fix)

### Bước 1: Thay thế `capture_ui_xml` bằng `capture_atx_session_ui` bounded trong `observe.py`
```python
# python_runner/flows/observe.py
    try:
        from automation_core.persistent_ui import capture_atx_session_ui

        timeout_sec = min(3.0, float(ctx.timeout("adb_seconds", 15)))
        atx = capture_atx_session_ui(
            ctx.adb,
            timeout=timeout_sec,
            restart_attempts=0,
        )
        if atx is not None and atx.xml and "<hierarchy" in atx.xml:
            pkgs = re.findall(r'package="([^"]+)"', atx.xml)
            if pkgs:
                for target_pkg in ("com.ss.android.ugc.trill", "com.zhiliaoapp.musically", "com.ss.android.ugc.aweme"):
                    if target_pkg in pkgs:
                        act_match = re.search(r'package="' + target_pkg + r'"[^>]*class="([^"]+)"', atx.xml)
                        activity = act_match.group(1) if act_match else None
                        return {"package": target_pkg, "activity": activity}
                non_system = [p for p in pkgs if p != "com.android.systemui"]
                package = non_system[0] if non_system else pkgs[0]
                act_match = re.search(r'package="' + re.escape(package) + r'"[^>]*class="([^"]+)"', atx.xml)
                activity = act_match.group(1) if act_match else None
                return {"package": package, "activity": activity}
    except Exception:
        pass

    candidates = [
        ["dumpsys", "window"],
        ["dumpsys", "activity", "activities"],
    ]
    dumpsys_timeout = min(5.0, float(ctx.timeout("adb_seconds", 15)))
    for attempt in range(retries):
        for command in candidates:
            try:
                result = ctx.adb.shell(command, timeout=dumpsys_timeout)
```
- Không bao giờ fallthrough xuống `dump_current_ui`.
- Cap timeout của lệnh fallback dumpsys ở mức tối đa 5.0s.

### Bước 2: Bổ sung Pre-Tap Focus Settle Retry trong `calibrate_screens.py`
```python
# python_runner/flows/calibrate_screens.py -> tap_navigation_target()
    step = f"{prefix}/tap_{target.name}"
    focus = get_focused_activity(ctx)
    if not focus.get("package"):
        time.sleep(1.0)
        focus = get_focused_activity(ctx)

    expected_package = str(ctx.config.get("tiktok_package", "com.ss.android.ugc.trill"))
    safety = safety_check(
        focus_package=focus.get("package"),
        focus_activity=focus.get("activity"),
        expected_package=expected_package,
        artifact_path=str(ctx.artifacts.nested_dir(artifact_prefix, f"tap_{target.name}")),
        unknown_is_manual_needed=False,
    )
    if not safety.ok:
        if safety.reason == "focused package unavailable":
            try:
                quick_xml = capture_required_ui(
                    ctx.adb,
                    timeout=min(5.0, float(ctx.timeout("ui_capture_seconds", 60))),
                    artifact_dir=None,
                    recovery_package=expected_package,
                )
                if quick_xml and ("com.ss.android.ugc.trill" in quick_xml or "com.zhiliaoapp.musically" in quick_xml or "com.ss.android.ugc.aweme" in quick_xml):
                    safety = SafetyCheckResult("ok", "TikTok verified via UI XML", safety.artifact_path, focus_package=expected_package)
            except Exception:
                pass
```

### Bước 3: Settle WindowManager trước khi force-stop trong `feed_swipe_smoke.py`
```python
# python_runner/flows/feed_swipe_smoke.py -> _maybe_recover_navigation_from_add_phone()
    elif _is_launcher_focus_loss(ctx, captured):
        captured_reason = str(captured.get("reason") or "").lower()
        if "package unavailable" in captured_reason:
            time.sleep(1.5)
            settled_focus = get_focused_activity(ctx)
            settled_pkg = str(settled_focus.get("package") or "")
            package_name = str(ctx.config.get("tiktok_package", "com.ss.android.ugc.trill"))
            tiktok_pkgs = {package_name, "com.ss.android.ugc.trill", "com.zhiliaoapp.musically", "com.ss.android.ugc.aweme"}
            if settled_pkg in tiktok_pkgs:
                return retry_navigation()

        package_name = str(ctx.config.get("tiktok_package", "com.ss.android.ugc.trill"))
```

---

## 4. Verification & Unit Tests
- Test file: `python_runner/tests/test_navigation_focus_recovery.py`
- Test mới: `test_pre_tap_settle_retry_when_initially_none`
- Chạy: `python -m unittest python_runner/tests/test_navigation_focus_recovery.py` -> Pass 5/5 (100%).
