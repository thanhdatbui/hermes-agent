# Case 116: Fast Focus Polling, Pre-Tap Focus Settle, and Test Runner Import Hygiene

## 1. Bối cảnh & Nguyên nhân lỗi
- **Stall 5 phút trong `get_focused_activity` (`observe.py`):** Khi gọi `capture_ui_xml`, nếu ATX agent chưa sẵn sàng hoặc gặp timeout, hàm này thực hiện provisioning check và retries với timeout lớn (15s x retries x 2 lệnh dumpsys), dẫn tới hiện tượng treo 5-10 phút trong các vòng lặp kiểm tra focus.
- **Mất focus thoáng qua trước khi tap navigation (`calibrate_screens.py`):** Khi vừa chuyển cảnh hoặc sau swipe, WindowManager chưa kịp cập nhật hoặc UI XML chưa settle khiến `get_focused_activity(ctx)` trả về `{"package": None, "activity": None}`. Nếu chạy ngay `safety_check`, runner sẽ kết luận `focused package unavailable` và dừng phiên sớm dù TikTok vẫn đang ở foreground.
- **Relaunch vội khi launcher focus loss do "package unavailable" (`feed_swipe_smoke.py`):** Trong `_maybe_recover_navigation_from_add_phone`, khi gặp lỗi `"package unavailable"`, flow lập tức force-stop và relaunch app thay vì chờ 1-2s cho UI settle.

## 2. Giải pháp chuẩn (Case 116 Architecture)

### A. Tối ưu `get_focused_activity` (`observe.py`)
- Chuyển sang gọi trực tiếp `capture_atx_session_ui` với timeout ngắn (tối đa 3.0s) và `restart_attempts=0` để fail-fast khi ATX bận, không treo provisioning.
- Giới hạn timeout của lệnh fallback `dumpsys` ở mức `<= 5.0s`.
```python
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
                    return {"package": target_pkg, "activity": act_match.group(1) if act_match else None}
            non_system = [p for p in pkgs if p != "com.android.systemui"]
            package = non_system[0] if non_system else pkgs[0]
            act_match = re.search(r'package="' + re.escape(package) + r'"[^>]*class="([^"]+)"', atx.xml)
            return {"package": package, "activity": act_match.group(1) if act_match else None}
except Exception:
    pass

candidates = [["dumpsys", "window"], ["dumpsys", "activity", "activities"]]
dumpsys_timeout = min(5.0, float(ctx.timeout("adb_seconds", 15)))
for attempt in range(retries):
    for command in candidates:
        try:
            result = ctx.adb.shell(command, timeout=dumpsys_timeout)
```

### B. Pre-tap Settle Retry & XML Fallback (`calibrate_screens.py`)
Trong `tap_navigation_target`:
1. Nếu `not focus.get("package")`: sleep 1.0s và query lại `get_focused_activity(ctx)`.
2. Nếu `safety_check` trả về `safety.reason == "focused package unavailable"`: thử `capture_required_ui` với timeout 5.0s. Nếu XML chứa package TikTok hợp lệ, ghi đè `safety = SafetyCheckResult("ok", "TikTok verified via UI XML", ...)`.
3. Kiểm tra lại `if not safety.ok:` trước khi log lỗi và return fail.

### C. Launcher Focus Loss Grace Period (`feed_swipe_smoke.py`)
Trong `_maybe_recover_navigation_from_add_phone` tại nhánh `elif _is_launcher_focus_loss(ctx, captured):`:
```python
captured_reason = str(captured.get("reason") or "").lower()
if "package unavailable" in captured_reason:
    time.sleep(1.5)
    settled_focus = get_focused_activity(ctx)
    settled_pkg = str(settled_focus.get("package") or "")
    package_name = str(ctx.config.get("tiktok_package", "com.ss.android.ugc.trill"))
    tiktok_pkgs = {package_name, "com.ss.android.ugc.trill", "com.zhiliaoapp.musically", "com.ss.android.ugc.aweme"}
    if settled_pkg in tiktok_pkgs:
        return retry_navigation()
```

## 3. Pitfalls khi làm việc trên Farm Repo (`tiktok-luot nuoi acc`)

### Pitfall 1: Lỗi Import `_path_setup` khi chạy unittest từ Repo Root
- **Hiện tượng:** Chạy `python -m unittest python_runner/tests/test_foo.py` báo `ModuleNotFoundError: No module named '_path_setup'`.
- **Nguyên nhân:** Python `unittest` module loader không tự động đưa thư mục chứa file test vào `sys.path` khi truyền đường dẫn file từ thư mục cha.
- **Cách xử lý chuẩn trong test file:**
```python
try:
    import _path_setup  # noqa: F401
except ModuleNotFoundError:
    import sys
    from pathlib import Path

    _tests_dir = Path(__file__).resolve().parent
    if str(_tests_dir) not in sys.path:
        sys.path.insert(0, str(_tests_dir))
    import _path_setup  # noqa: F401
```

### Pitfall 2: CẤM Grep đệ quy toàn bộ thư mục repo
- Không bao giờ chạy `grep -rn "..." D:/Taadaa/tiktok-luot nuoi acc/`. Ổ đĩa farm chứa số lượng lớn file logs, virtualenvs và artifacts khiến lệnh grep bị nghẽn và timeout (900s).
- Luôn chỉ định file đích cụ thể: `grep -n "..." path/to/file.py` hoặc đọc trực tiếp bằng công cụ đọc file.
