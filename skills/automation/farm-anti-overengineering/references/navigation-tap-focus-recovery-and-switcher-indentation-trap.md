# Navigation Tap Focus Recovery & Account Switcher Indentation Trap (06/09/2026)

## 1. Bối cảnh & Hiện trường sự cố
- **Alert:** `[FARM ALERT: MÁY 69] DỪNG PHIÊN`
- **Quy trình:** Nuôi Acc / Lướt Feed (`tiktok-luot nuoi acc`)
- **Thiết bị:** Máy 69 (Samsung Galaxy S7, serial `ce12160c386c913101`), nick `@tranthibich3499`.
- **Triệu chứng hiển thị:** `TikTok focus lost after navigation tap: unknown`.
- **Hiện trường:** Màn hình điện thoại thực tế đang dừng tại tab **Hồ sơ** (`@tranthibich3499`), app TikTok vẫn đang mở hoàn toàn bình thường, không hề bị crash hay văng launcher.

---

## 2. Phân tích nguyên nhân gốc rễ 2 tầng (Two-Layer Root Cause)

### Tầng 1: Lỗi bề mặt (Symptom) — Transient Dumpsys Focus Drop trong `calibrate_screens.py`
- Tại hàm `tap_navigation_target(ctx, target, ...)` trong `python_runner/flows/calibrate_screens.py`:
  - Sau khi tap tab điều hướng (ví dụ tab Trang chủ hoặc tab Profile), hàm gọi `post_focus = get_focused_activity(ctx)` để lấy package/activity hiện tại qua `dumpsys window` / `dumpsys activity`.
  - Trên các thiết bị phần cứng cũ (Samsung Galaxy S7 Android 8), ngay sau thao tác tap chuyển tab, UI TikTok đang trong quá trình chuyển tiếp (transition rendering / window recreation), câu lệnh `dumpsys` query ngay lúc này có thể trả về chuỗi rỗng (`None` hoặc `""`).
  - Khi `post_package == ""`, code gán chuỗi định dạng:
    ```python
    reason = f"TikTok focus lost after navigation tap: {post_package or 'unknown'}"
    ```
    và fail `NavigationResult(False, ...)` dù ứng dụng TikTok vẫn đang mở trên màn hình.
- **Giải pháp 2 lớp Fallback Focus Recovery:**
  1. *Lớp 1 (Top Resumed Activity):* Kiểm tra `dumpsys activity activities` tìm `mResumedActivity` hoặc `topResumedActivity` có chứa `expected_package`.
  2. *Lớp 2 (UI XML Hierarchy):* Dùng `capture_required_ui` kiểm tra xem XML tree hiện tại có chứa package của TikTok (`com.zhiliaoapp.musically` / `com.ss.android.ugc.trill`) hay không trước khi bấm Back hoặc kết luận fail.

### Tầng 2: Lỗi khởi nguồn (Trigger) — Cạm bẫy thụt lề (Indentation Trap) trong `verify_and_switch_profile`
- Tại `python_runner/flows/feed_swipe_smoke.py` (`verify_and_switch_profile`):
  - Khối `try: verify_selected_account(...) verified = True` đã xác minh thành công tài khoản hiện tại đang ở đúng profile.
  - Tuy nhiên, khối logic so khớp placeholder `if is_placeholder_candidate: ... else: ...` bị thụt lề sai (nằm ngoài khối `except AccountSwitcherError:`).
  - Khi không có ngoại lệ, luồng thực thi vẫn chạy thẳng vào khối placeholder check bên ngoài, truy cập vào các biến `recaptured_xml`, `recaptured_username`, `recaptured_display_name` vốn chỉ được sinh ra trong khối `except` khi mở account switcher popup.
  - Hậu quả kép:
    1. Khi chạy canary, ném ngoại lệ: `UnboundLocalError: cannot access local variable 'recaptured_xml' where it is not associated with a value`.
    2. Trong luồng bình thường, điều kiện `verified` bị đánh giá sai thành `False`, khiến runner ngộ nhận tài khoản chưa đúng và kích hoạt chuỗi tap điều hướng không cần thiết, đẩy thiết bị vào nhánh lỗi `focus lost: unknown` ở Tầng 1.

---

## 3. Bản vá chuẩn (Patch Specification)

### A. Trong `feed_swipe_smoke.py` (`verify_and_switch_profile`):
1. Luôn khởi tạo giá trị an toàn mặc định trước khối `try`:
   ```python
   verified = False
   recaptured_xml = ""
   ```
2. Thụt lề toàn bộ khối `if is_placeholder_candidate: ... else: ...` nằm gọn bên trong khối `except AccountSwitcherError:`, đảm bảo chỉ thực hiện recapture matching khi việc verify trực tiếp bằng XML ban đầu thất bại.

### B. Trong `calibrate_screens.py` (`tap_navigation_target`):
Thêm khối fallback trước khi kết luận `not recovered_focus`:
```python
if not recovered_focus:
    if not post_package or post_package == "unknown":
        try:
            dump_res = ctx.adb.shell(["dumpsys", "activity", "activities"], timeout=ctx.timeout("adb_seconds", 10))
            dump_str = dump_res if isinstance(dump_res, str) else str(dump_res or "")
            for line in dump_str.splitlines():
                if any(kw in line for kw in ("mResumedActivity", "topResumedActivity", "ResumedActivity")) and expected_package in line:
                    recovered_focus = True
                    post_package = expected_package
                    break
        except Exception:
            pass

    if not recovered_focus and (not post_package or post_package == "unknown"):
        try:
            quick_ui = capture_required_ui(ctx.adb, timeout=ctx.timeout("ui_capture_seconds", 10))
            if quick_ui and expected_package in quick_ui:
                recovered_focus = True
                post_package = expected_package
        except Exception:
            pass
```

---

## 4. Quy trình kiểm chứng Canary (Canary Verification)
1. Dọn stale lock: `python "D:/Taadaa/tiktok-luot nuoi acc/scripts/reap-dead-owner-locks.py"`.
2. Chạy với `env -u PYTHONPATH`:
   ```bash
   env -u PYTHONPATH powershell.exe -ExecutionPolicy Bypass -File "D:\Taadaa\tiktok-luot nuoi acc\scripts\run-feed-session.ps1" -Machines 69 -Row 1 -RecoveryTestSwipes 2 -SkipAccountWorkbookSync -Run
   ```
3. Kết quả kỳ vọng: Exit code `0`, `total_swipes_completed: 2`, `final_status: success`.
