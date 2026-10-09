# Case 112: Tự Động Phục Hồi Focus Khi Bị Mất Focus Hoặc Unknown Sau Navigation Tap

## Bối Cảnh Sự Cố (Máy 6 - Nick alemafxjvxw)
- **Triệu chứng:** Alert `TikTok focus lost after navigation tap: unknown`.
- **Nguyên nhân cốt lõi:** Sau cú tap điều hướng trong `tap_navigation_target()` (`python_runner/flows/calibrate_screens.py`), WindowManager của Samsung chuyển cảnh hoặc ATX XML chưa kịp settle khiến `get_focused_activity(ctx)` trả về `{"package": None, "activity": None}` (`post_package = ""`).
- **Hậu quả nếu thiếu xử lý:** Khi `post_package` rỗng, code không thử settle và bỏ qua khối recovery launcher/systemui, dẫn tới kết luận ngay `TikTok focus lost after navigation tap: unknown`, làm dừng phiên feed oan uổng dù TikTok vẫn đang chạy nền hoặc đang chuyển cảnh.

## Quy Trình Xử Lý Chuẩn (Pattern Fix)

### 1. Nhịp Settle Retry (Tránh false alert do chuyển cảnh)
Nếu `not post_package` ngay sau tap:
```python
if not post_package:
    time.sleep(1.0)
    post_focus = get_focused_activity(ctx)
    post_package = str(post_focus.get("package") or "")
    post_activity = post_focus.get("activity")
```

### 2. Mở Rộng Nhận Diện Launcher / SystemUI / Unknown
Không chỉ so sánh cứng với một vài package launcher:
```python
is_launcher_or_systemui_or_unknown = (
    not post_package
    or post_package in {
        "com.android.systemui",
        "com.sec.android.app.launcher",
        "com.android.launcher",
        "com.android.launcher3",
        "com.google.android.apps.nexuslauncher",
    }
    or "launcher" in post_package.lower()
    or "systemui" in post_package.lower()
)
```

### 3. Phục Hồi Focus 2 Tầng (2-Tier Focus Recovery)
- **Tầng 1 (Back Key):** Gửi `input keyevent 4` (KEYCODE_BACK). Chờ 1.2s và kiểm tra lại focus.
- **Tầng 2 (Monkey Launch):** Nếu sau phím BACK mà `retry_pkg != expected_package` (ví dụ vẫn ở màn hình chính launcher), gọi:
  ```python
  ctx.adb.shell(
      ["monkey", "-p", expected_package, "-c", "android.intent.category.LAUNCHER", "1"],
      timeout=ctx.timeout("adb_seconds", 15),
  )
  ```
  Chờ 1.5s và xác nhận `monkey_pkg == expected_package`.

### 4. Guard Permission Popup
Chỉ kích hoạt kiểm tra và dismiss permission popup nếu chưa phục hồi được focus:
```python
if not recovered_focus and post_package in SYSTEM_PERMISSION_PACKAGES:
    ...
```

## Cảnh Báo Điều Tra (Investigation Pitfall)
- **CẤM TUYỆT ĐỐI:** Chạy `grep -rn` quét diện rộng trong `python_runner` hoặc repo không có giới hạn file. Điều này dẫn tới timeout 900s do duyệt qua các file cache, fixtures hoặc .git lớn.
- **QUY TẮC:** Luôn mở trực tiếp file flow cụ thể (`flows/calibrate_screens.py`, `flows/feed_swipe_smoke.py`, `flows/device_prepare.py`) hoặc dùng ripgrep với `--glob` thu hẹp.
