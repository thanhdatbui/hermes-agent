# Profile Verification Mismatch: SystemUI Focus Trap, Unverified Swipe Down & Thẻ Carousel TikTok GO (Case 120, 2026-09-06, Máy 25)

## 1. Hiện tượng & Triệu chứng thực tế (Alert Máy 25)
- **Thiết bị:** Máy 25 | Serial: `ce02182261a6a62105` | Nick: `thao.phan206` (Row 1).
- **Quy trình:** Nuôi Acc / Lướt Feed (`tiktok-luot nuoi acc`).
- **Triệu chứng Alert:** `profile verification mismatch: profile account mismatch`.
- **Màn hình dừng:** Đang mở thẻ quảng bá dạng carousel **"TikTok GO"** ("Khám phá hòn ngọc địa phương và chia sẻ những câu chuyện của bạn với TikTok GO", có nút "Không quan tâm", "Khám phá" và ký hiệu vuốt lên ︽).
- **Thực tế lướt video:** Đã hoàn thành trọn vẹn **8/8 video** (`total_swipes_completed: 8`), không hề kẹt trong vòng lặp lướt feed.

---

## 2. Phân tích nguyên nhân gốc rễ (Root Cause Analysis)

### Root Cause 1: SystemUI Focus Trap & False Pass trong `tap_navigation_target` (`calibrate_screens.py`)
- Trên màn hình Samsung Galaxy S7 (1080x1920), tab Hồ sơ ở đáy màn hình có bounds `[864, 1794][1080, 1920]`, tọa độ tâm tap là `(972, 1857)`.
- Vị trí `y=1857` nằm sát mép dưới cùng của màn hình cảm ứng, nơi thanh điều hướng ảo/Recent Apps của Samsung SystemUI hoạt động. Khi tap, sự kiện chạm làm `com.android.systemui` chiếm focus tạm thời (`post_package: com.android.systemui`).
- Hàm `tap_navigation_target` kích hoạt khối phục hồi `recover_tiktok_focus_after_systemui_tap` gửi phím `BACK` (`keyevent 4`) để đưa TikTok về foreground.
- **Lỗi logic:** Phím `BACK` này đã hủy bỏ hiệu ứng chuyển tab sang Hồ sơ, giữ TikTok ở lại **Trang chủ (Home Feed)**. Tuy nhiên, `tap_navigation_target` thấy `post_package == expected_package` liền trả về `NavigationResult(True, "pass")` — báo thành công giả tạo (false-positive).

### Root Cause 2: Unverified Swipe Down trong `_verify_profile_after_session` (`feed_swipe_smoke.py`)
- Khi `tap_navigation_target` báo thành công giả, TikTok vẫn đang ở Trang chủ (`profile_screen_confirmed = False`).
- Tại `_verify_profile_after_session`, do không tìm thấy username `thao.phan206` trên Trang chủ, script kết luận `not matched`.
- Đoạn mã cũ ngay lập tức kích hoạt nhánh cuộn ngược:
  ```python
  if not matched:
      # Cuộn ngược từ trên xuống dưới (swipe down) để kéo header chứa username lộ diện
      ctx.adb.shell(["input", "swipe", "540", "600", "540", "1500", "350"])
  ```
- **Hậu quả nghiêm trọng:** Lệnh `swipe 540 600 -> 540 1500` (vuốt từ trên xuống dưới) khi thực thi trên Trang chủ Home Feed đã kích hoạt cử chỉ **pull-to-refresh / kéo ngược feed**, làm bung ra thẻ quảng cáo carousel **"TikTok GO"**.
- Script sau đó đọc lại XML trên Trang chủ, vẫn không có username Profile, dẫn đến fail-closed `profile account mismatch` và kích hoạt Farm Alert.

---

## 3. Giải pháp khắc phục chuẩn (Standard Fix)

### Fix 1: Bắt buộc Retry Tap Navigation sau khi Recover Focus (`calibrate_screens.py`)
Trong `tap_navigation_target`:
Khi `recovered_focus` thành công sau khi recover focus từ SystemUI/Launcher (qua `KEYCODE_BACK` hoặc monkey), **KHÔNG ĐƯỢC** trả `NavigationResult(True, ...)` ngay. Bắt buộc retry tap lại tab mục tiêu:
```python
if recovered_focus:
    ctx.logger.log(
        device_id=ctx.device_id,
        account=ctx.account,
        step=step,
        action="retry_tap_navigation_target_after_focus_recovery",
        selector=selector,
        result="retry",
        extra={"target": target.name, "x": x, "y": y},
    )
    retry_tap = ctx.adb.shell(["input", "tap", str(x), str(y)], timeout=ctx.timeout("adb_seconds", 15))
    time.sleep(1.2)
    post_focus = get_focused_activity(ctx)
    post_package = str(post_focus.get("package") or "")
    post_activity = post_focus.get("activity")
    recovered_focus = (post_package == expected_package)
```

### Fix 2: Gating chặt chẽ lệnh Swipe Down & Retry Tap Profile (`feed_swipe_smoke.py`)
Trong `_verify_profile_after_session`:
- CẤM TUYỆT ĐỐI chạy `swipe down` khi chưa ở màn hình Hồ sơ (`not profile_screen_confirmed`).
- Nếu `not profile_screen_confirmed`: Bắt buộc gọi lại `tap_navigation_target` điều hướng tab Hồ sơ tối đa 2 lần.
- CHỈ KHI `profile_screen_confirmed is True` (đã ở Profile) nhưng chưa thấy username header mới được phép chạy `swipe down 540 600 -> 540 1500 350`.

```python
if not matched:
    if not profile_screen_confirmed:
        retry_navigation = tap_navigation_target(
            ctx,
            CalibrationTarget("profile", ("Hồ sơ", "Profile"), "bottom", required=True),
            artifact_prefix=f"{artifact_prefix}_profile_nav_retry",
            log_prefix=f"{artifact_prefix}_profile_nav_retry",
        )
        if retry_navigation.ok:
            time.sleep(1.2)
            nav_retry_xml = _capture_xml_text(ctx, f"{artifact_prefix}_profile_nav_retry")
            if nav_retry_xml:
                _apply_profile_capture_metadata(row, ctx.adb)
                if _profile_screen_confirmed_from_xml(nav_retry_xml):
                    xml_text = nav_retry_xml
                    profile_screen_confirmed = True
                    nav_id = _profile_identity_from_xml(nav_retry_xml)
                    nav_user = str(nav_id.get("username") or "")
                    if bool(expected) and expected == nav_user.strip().lstrip("@").lower():
                        matched = True
                        username = nav_user
                        display_name = str(nav_id.get("display_name") or "")

if not matched and profile_screen_confirmed:
    try:
        ctx.adb.shell(["input", "swipe", "540", "600", "540", "1500", "350"], timeout=ctx.timeout("adb_seconds", 15))
        time.sleep(1.0)
        scroll_retry_xml = _capture_xml_text(ctx, f"{artifact_prefix}_profile_scroll_retry")
        ...
```

### Fix 3: Đăng ký Handler Thẻ Carousel "TikTok GO" (`benign_popup_registry.py`)
Đăng ký handler `tiktok_go_card` với priority 70:
- **Detector (`_detect_tiktok_go_card`):** Nhận diện khi text/desc hoặc OCR chứa `"TikTok GO"` hoặc (`"Khám phá hòn ngọc địa phương"` / `"Khám phá những xu hướng mới nhất"`) VÀ có nút `"Không quan tâm"` hoặc `"Khám phá"`.
- **Dismisser (`_dismiss_tiktok_go_card`):** Ưu tiên tìm element có text/desc `"Không quan tâm"` (`"Not interested"`) để tap. Nếu không tìm thấy, gửi lệnh swipe up nhẹ `["input", "swipe", "540", "1400", "540", "600", "300"]` theo ký hiệu `︽` để trượt qua thẻ.

---

## 4. Kiểm chứng & Verification Evidence
- Unit test: `test_navigation_focus_recovery.py` (5/5 tests passed 100%), `test_verify_profile_nav_retry.py` (2/2 tests passed 100%).
- Live Canary Máy 25: `powershell.exe -ExecutionPolicy Bypass -File "D:\Taadaa\tiktok-luot nuoi acc\scripts\run-feed-session.ps1" -Machines 25 -Row 1 -RecoveryTestSwipes 2 -SkipAccountWorkbookSync -Run` đạt `final_status: success`, 2/2 swipes completed, verify profile `matched`, device lock và Launcher focus giải phóng sạch.
