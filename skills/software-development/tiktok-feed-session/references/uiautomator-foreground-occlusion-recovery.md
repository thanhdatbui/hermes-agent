# UiAutomator Foreground Occlusion Recovery Pattern

## Bối cảnh & Nguyên nhân
Trên farm Android nuôi acc TikTok (`tiktok-luot nuoi acc`), package `com.github.uiautomator` (hoặc `com.github.uiautomator.test`) có thể vô tình chiếm foreground:
1. Do các hàm phục hồi cũ trong `capture_recovery.py` gọi `am start -n com.github.uiautomator/.MainActivity` hoặc `monkey -p com.github.uiautomator 1`.
2. Do stub service/crash restart tự động kích hoạt UI của uiautomator.

Khi `com.github.uiautomator` chiếm foreground:
- `observe_current_screen` đọc dumpsys/UI thấy package `com.github.uiautomator` -> gán `SAFETY_FAILED` ("TikTok focus lost").
- `_verify_tiktok_focus_with_retries` và `prepare_tiktok_app_for_automation` kiểm tra foreground package thấy khác TikTok -> báo lỗi verify focus thất bại sau N attempts.

## Giải pháp bền vững (Durable Pattern)

### 1. Loại bỏ các lệnh khởi chạy MainActivity/Monkey của UiAutomator
Trong `capture_recovery.py`:
- Cấm gọi `monkey -p com.github.uiautomator 1` (khi dính exit 137).
- Thay thế các lệnh `am start -n com.github.uiautomator/.MainActivity` bằng evidence ghi nhận `{"attempted": False}`. UiAutomator chỉ cần background service (`am start-foreground-service`) và ATX-agent daemon (`/data/local/tmp/atx-agent server -d`), tuyệt đối không cần mở MainActivity lên màn hình.

### 2. Tự động phục hồi khi UiAutomator che màn hình (Occlusion Recovery)
Định nghĩa danh sách package nhận diện:
`UIAUTOMATOR_PACKAGES = ("com.github.uiautomator", "com.github.uiautomator.test")`

Hàm xử lý tiêu chuẩn trong `flows/observe.py`:
```python
def recover_uiautomator_occlusion(ctx: DeviceContext, package_name: str) -> dict[str, str | None]:
    timeout = ctx.timeout("adb_seconds", 15) if hasattr(ctx, "timeout") else 15.0
    try:
        ctx.adb.shell(["am", "force-stop", "com.github.uiautomator"], timeout=timeout)
        ctx.adb.shell(["input", "keyevent", "3"], timeout=timeout)
        ctx.adb.shell(
            ["monkey", "-p", package_name, "-c", "android.intent.category.LAUNCHER", "1"],
            timeout=timeout,
        )
    except Exception:
        pass
    time.sleep(1.0)
    return get_focused_activity(ctx)
```

Tích hợp vào:
- `observe.py::observe_current_screen`: Kiểm tra `if focus.get("package") in UIAUTOMATOR_PACKAGES: focus = recover_uiautomator_occlusion(ctx, expected_package)`. Log action `recover_uiautomator_occlusion` trước khi xét `safety_check`.
- `device_prepare.py::_verify_tiktok_focus_with_retries`: Khi `focused_package in UIAUTOMATOR_PACKAGES`, gọi recovery trước khi đánh giá `ok = focused_package == package_name`.
- `device_prepare.py::prepare_tiktok_app_for_automation`: Trong `read_focus()`, nếu phát hiện uiautomator foreground thì tự động trigger recovery.

## Pitfalls khi viết Unit Test
1. **Mock seam leaking vào `flows.observe`**: Khi `device_prepare.py` gọi `recover_uiautomator_occlusion`, hàm này nằm trong `flows.observe` và gọi trực tiếp `flows.observe.get_focused_activity`. Nếu test chỉ patch `flows.device_prepare.get_focused_activity`, hàm trong `flows.observe` sẽ không được mock và chạy fallback thật (gọi `capture_ui_xml` / socket ADB -> timeout). Phải patch `flows.observe.get_focused_activity` hoặc patch cả hai.
2. **Mock `time.sleep`**: `core_prepare_app_for_automation` và `device_prepare` có vòng lặp retry focus với `time.sleep(1.5)`. Cần patch `time.sleep` ở cả hai module để test chạy nhanh và tránh timeout.
