# One-Tap "Chào Mừng Bạn Trở Lại" Login Screen & Feed Preflight Auto-Recovery (10/10/2026)

## 1. Hiện Tượng & Căn Nguyên
- **Hiện tượng**: Ca lướt feed (feed session) mở app và tap tab Hồ sơ (`tap_profile`), gặp màn hình **"Chào mừng bạn trở lại"** (One-tap Login selector hiển thị danh sách các tài khoản lưu session). 
- Bot Telegram bắn ngay cảnh báo đỏ:
  ```text
  ⚠️ [P0 CẢNH BÁO MẤT PHIÊN / VĂNG ACCOUNT]: Máy M... login/account screen detected
  ```
- **Căn nguyên thực tế**:
  1. Các tài khoản hiển thị trên màn hình One-tap **vẫn còn nguyên 100% session** trong cache TikTok, không hề bị logout hay chết session.
  2. Tuy nhiên, do chưa có tài khoản nào active trong Profile chính, bước tiền kiểm `profile_preflight_identity_guard` phát hiện màn hình đăng nhập và gắn nhãn `manual-needed:login` (`login/account screen detected`).

## 2. Điểm Nghẽn Logic Trong Feed Runner (`feed_swipe_smoke.py`)
- **Thiết kế ban đầu của User**: Hệ thống có sẵn hàm tự nạp nick `_maybe_recover_missing_account_via_login(ctx, expected, ...)` gọi `tiktok_login_v1.py`.
- **Tại sao auto-login không tự chạy?**:
  - Hàm `_maybe_recover_missing_account_via_login` trước đây chỉ được đặt ở nhánh `if _is_account_switcher_missing_expected_reason(last_reason):` (dòng ~18451), tức là **chỉ kích hoạt sau khi đã mở được Account Switcher bottom sheet từ Profile thành công** mà không tìm thấy nick đích.
  - Khi gặp màn hình One-tap "Chào mừng bạn trở lại", hàm `_read_profile_identity_with_add_phone_guard` trả về `identity_manual_row` (do `manual-needed:login`).
  - Hàm `verify_and_switch_profile` thấy `identity_manual_row` là lập tức return `_profile_manual_preflight_row` với `switch_reason="profile identity blocked by manual-needed screen"`.
  - **Hậu quả**: Tiến trình bị chặn ngay tại cửa kiểm tra trước khi kịp bung Account Switcher, nhánh gọi auto-login hoàn toàn bị bỏ qua!

## 3. Giải Pháp Khắc Phục Chuẩn Mực O(1)
Trong `python_runner/flows/feed_swipe_smoke.py` (`verify_and_switch_profile`):
```python
    identity_manual_row = identity.get("manual_row")

    if isinstance(identity_manual_row, dict):
        if allow_auto_reconcile and any("login" in str(identity_manual_row.get(k) or "").lower() for k in ("detected", "safety_reason", "reason")):
            if _maybe_recover_missing_account_via_login(ctx, expected, results=results, max_swipes=max_swipes, result_kwargs=result_kwargs):
                ctx.logger.log(
                    device_id=ctx.device_id,
                    account=ctx.account,
                    step=f"{SESSION_ARTIFACT_PREFIX}/profile_preflight",
                    action="auto_login_recovered_from_login_screen",
                    result="retry",
                    extra={"reason": f"auto-login succeeded after login screen for {expected}", "expected_account": expected},
                )
                return verify_and_switch_profile(ctx, expected_account, results=results, max_swipes=max_swipes, result_kwargs=result_kwargs, allow_auto_reconcile=False)

        row = _profile_manual_preflight_row(...)
        ...
```
- Khi `identity_manual_row` mang cờ `login`: Tự động gọi `_maybe_recover_missing_account_via_login` để nạp hoặc chuyển vào tài khoản đích qua `tiktok_login_v1.py`.
- Khi nạp thành công: Re-run `verify_and_switch_profile` với `allow_auto_reconcile=False` (chống vòng lặp vô tận) để xác nhận Profile đã active và tiếp tục lướt feed.

## 4. Cạm Bẫy Phụ Trong `dismiss_profile_overlays` (`social_reg_v1.py`)
- **Bẫy regex thanh trạng thái**: Bộ lọc modal `if any(k in flat for k in ["add phone", "them so dien thoai", "so dien thoai cua ban"]):` vô tình khớp chuỗi `"dien thoai cua ban"` từ thông báo Samsung trên thanh trạng thái (*"Tìm di động của bạn: Nếu bạn mất điện thoại thì sao?"*).
- **Hậu quả**: Script hiểu nhầm màn hình One-tap là popup thêm số điện thoại và tap nút `Đóng` (`z7l`), vô tình đóng mất màn hình One-tap Login!
- **Khắc phục**: Trong `dismiss_profile_overlays`, đặt guard thoát sớm nếu màn hình là One-tap:
  ```python
  if any(k in flat for k in ["chao mung ban tro lai", "welcome back", "them tai khoan khac"]):
      return
  ```
