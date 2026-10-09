# Profile Navigation Retry & TikTok GO Card Handling

## 1. Profile Verification Navigation Retry (`feed_swipe_smoke.py`)

### Root Cause & Pitfall
- Trong quá trình xác thực profile (`feed_swipe_smoke.py`), nếu tài khoản chưa hiện đúng username mong muốn:
  - Logic cũ: Tự động swipe down (`input swipe 540 600 540 1500 350`) để kéo lộ header chứa username.
  - **Pitfall**: Nếu điều hướng trước đó thất bại hoặc bị chặn bởi popup/card, máy vẫn đang ở tab Trang chủ (For You). Việc vuốt swipe down ở Trang chủ sẽ kích hoạt kéo reload feed thay vì lộ profile header.
- **Quy tắc bắt buộc**:
  - Tuyệt đối KHÔNG vuốt swipe down nếu chưa xác nhận đang ở màn hình Profile (`not profile_screen_confirmed`).
  - Phải thực hiện retry điều hướng vào tab Profile trước:
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
        # Chỉ vuốt khi ĐÃ xác nhận ở profile screen
        try:
            ctx.adb.shell(["input", "swipe", "540", "600", "540", "1500", "350"], timeout=ctx.timeout("adb_seconds", 15))
    ```

---

## 2. TikTok GO Card Dismissal (`benign_popup_registry.py`)

### Đặc điểm nhận dạng
- Card giới thiệu TikTok GO trên feed:
  - Text chứa: `"tiktok go"`, `"khám phá hòn ngọc địa phương"`, hoặc `"khám phá những xu hướng mới nhất"`.
  - Nút bấm chứa: `"không quan tâm"`, `"not interested"`, hoặc `"khám phá"`.

### Dismiss Handler
- Ưu tiên tìm element `"không quan tâm"` hoặc `"not interested"` trong XML hierarchy và tap vào toạ độ tâm bounds.
- Fallback: Nếu không tìm thấy bounds, vuốt nhẹ lên (`input swipe 540 1400 540 600 300`) để trượt qua card.
- **Import Pitfall trong `benign_popup_registry.py`**:
  - Khi viết handler trong file này, bắt buộc lazy-import trong hàm hoặc kiểm tra scope:
    ```python
    from .benign_popup import PopupDismissResult
    from automation_core.ui import iter_elements, parse_bounds
    ```
  - Nếu thiếu, các unit test hoặc runtime gọi handler sẽ văng `NameError: name 'iter_elements' is not defined` hoặc `NameError: name 'PopupDismissResult' is not defined`.

---

## 3. Unit Test Verification
- Luôn kèm unit test kiểm tra detect & dismiss:
  ```bash
  PYTHONPATH="D:/Taadaa/automation-core/src;D:/Taadaa/tiktok-luot nuoi acc/python_runner" python -m unittest python_runner/tests/test_verify_profile_nav_retry.py
  PYTHONPATH="D:/Taadaa/automation-core/src;D:/Taadaa/tiktok-luot nuoi acc/python_runner" python -m unittest python_runner/tests/test_navigation_focus_recovery.py
  ```
