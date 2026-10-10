# One-tap Welcome Back ("Chào mừng bạn trở lại") Guard Bypass & Auto-Login Recovery Trap

> 📎 Date: 2026-10-10
> 📎 Repos: `tiktok-luot nuoi acc` (`python_runner`), `Tiktok_Reg` (`tiktok_login_v1.py`), `tools/recover_missing_tiktok_login.py`

## 1. Triệu chứng & Vấn đề Cốt Lõi
- **Hiện tượng**: Ca nuôi lướt feed (VD: M261 Row 4 `@chikute343`) văng alert Telegram `⚠️ [P0 CẢNH BÁO MẤT PHIÊN / VĂNG ACCOUNT]: login/account screen detected`.
- **Cảm giác của Operator**: "Máy cứ bị văng acc lạ thế nào ấy, trong khi đã thiết kế script tự nạp nick khi thiếu (`_maybe_recover_missing_account_via_login`) mà tại sao không tự chạy?"
- **Thực tế giao diện**:
  1. Các tài khoản cũ (VD: `@lamhongloan1907`, `@thuthanh2911`, `@huynhngocloc1998`) **không hề bị mất phiên hay logout**. Chúng vẫn nằm nguyên 100% trong danh sách lưu session nhanh của màn hình **"Chào mừng bạn trở lại"** (One-tap Login multi-account selector).
  2. Nick mục tiêu của ca nuôi (VD: `@chikute343`) thực chất **chưa từng được đăng nhập trên máy**.

## 2. Điểm Nghẽn Kỹ Thuật (Architecture / Gate Mismatch)
Tại sao cơ chế tự nạp nick `_maybe_recover_missing_account_via_login` không tự động kích hoạt?
1. **Vị trí hook quá sâu trong luồng Switcher**:
   - Trong `flows/feed_swipe_smoke.py`, `_maybe_recover_missing_account_via_login` chỉ được hook tại dòng ~18451 bên trong nhánh:
     ```python
     if _is_account_switcher_missing_expected_reason(last_reason):
         if allow_auto_reconcile:
             if _maybe_recover_missing_account_via_login(...):
                 ...
     ```
   - Điều kiện tiên quyết: Máy phải đang có một Profile active, cuộn và mở menu Account Switcher bottom sheet thành công, sau đó duyệt danh sách switcher mà không thấy nick đích (`account-switcher-missing-expected`).
2. **Cửa ngõ tiền kiểm chặn cụt (Fail-closed Profile Guard)**:
   - Khi máy chưa có profile active nào ở foreground, bấm vào tab Hồ sơ (`tap_profile`) sẽ rơi thẳng vào màn hình **"Chào mừng bạn trở lại"**.
   - Bộ phân loại `profile_preflight_identity_guard` (dòng 15548 & 17736) quét thấy text *"Chào mừng bạn trở lại"* liền gán nhãn `manual-needed:login` (*login/account screen detected*).
   - Hàm `verify_and_switch_profile` thấy `identity_manual_row` là lập tức trả về `_profile_manual_preflight_row` với:
     ```python
     switch_reason = "profile identity blocked by manual-needed screen"
     ```
   - Quy trình thoát ngay lập tức, **hoàn toàn không chạm tới được Account Switcher hay đoạn gọi auto-login**!

## 3. Quy Chuẩn Xử Lý & Thiết Kế Khắc Phục Chuẩn
1. **Triage Hiện Trường**:
   - Không được vội kết luận tài khoản bị văng session. Kiểm tra XML/screenshot của `profile_preflight_identity_guard`.
   - Nếu thấy `Chào mừng bạn trở lại`:
     * Kiểm tra danh sách tài khoản lưu trên màn hình (các TextView `@...` kèm email che sao). Nếu nick mục tiêu nằm trong số đó: chỉ cần tap vào nick đó là active ngay session mà không cần mật khẩu/OTP.
     * Nếu nick mục tiêu KHÔNG có trong danh sách: Đây là tình trạng **chưa nạp nick (missing account)**, không phải văng session đột ngột.
2. **Quy trình nạp nick khẩn cấp (Coordinator Execution)**:
   - Chạy trực tiếp `tiktok_login_v1.py` với đúng cấu hình cluster (Admin vs Kibe):
     ```bash
     # Cụm Admin (STT >= 200):
     TAADAA_HOST_CONFIG="D:/Taadaa/machine-config/admin.yaml" \
     ADB_SERVER_SOCKET="tcp:192.168.110.119:5037" \
     python D:/Taadaa/Tiktok_Reg/tiktok_login_v1.py <STT> --email <nick> --ss --no-track
     ```
   - Chú ý: `tiktok_login_v1.py` đã có sẵn logic bypass màn hình "Chào mừng bạn trở lại" bằng cách tap *"Thêm tài khoản khác"* (`one_tap_bypass`).
3. **Cải tiến đã thực thi cho Feed Runner (`feed_swipe_smoke.py`)**:
   - Khi `verify_and_switch_profile` nhận `identity_manual_row` mang nhãn `login` (như `manual-needed:login` hoặc `login/account screen detected`):
     ```python
     if isinstance(identity_manual_row, dict):
         if allow_auto_reconcile and any("login" in str(identity_manual_row.get(k) or "").lower() for k in ("detected", "safety_reason", "reason")):
             if _maybe_recover_missing_account_via_login(ctx, expected, results=results, max_swipes=max_swipes, result_kwargs=result_kwargs):
                 ctx.logger.log(
                     device_id=ctx.device_id, account=ctx.account,
                     step=f"{SESSION_ARTIFACT_PREFIX}/profile_preflight",
                     action="auto_login_recovered_from_login_screen", result="retry",
                     extra={"reason": f"auto-login succeeded after login screen for {expected}", "expected_account": expected},
                 )
                 return verify_and_switch_profile(ctx, expected_account, results=results, max_swipes=max_swipes, result_kwargs=result_kwargs, allow_auto_reconcile=False)
     ```
   - Cơ chế này bẻ gãy việc fail-closed mù quáng, cho phép feed runner tự động gọi `tiktok_login_v1.py` để nạp hoặc kích hoạt tài khoản đích ngay tại chỗ, sau đó tự re-verify profile và tiếp tục lướt feed.

## 4. Ba Bẫy Tử Huyệt Khi Chạy Login Recovery (`tiktok_login_v1.py` & `social_reg_v1.py`)
1. **Bẫy Màn Hình "Hồ Sơ Khách" (Guest Profile Screen - `d01`)**:
   - *Hiện tượng*: Khi máy chưa có session nào active, vào Profile không có tên hay chevron `rv5`. Màn hình hiện text *"Đăng nhập vào tài khoản hiện có"* và nút to đỏ **`Đăng nhập`** (`rid='com.ss.android.ugc.trill:id/d01'`).
   - *Hậu quả cũ*: Script cố tìm `open_account_dropdown` và văng lỗi `[03_dropdown] Khong mo duoc account dropdown`.
   - *Khắc phục chuẩn*: Trong `ensure_login_entry_screen`, nếu phát hiện text *"dang nhap vao tai khoan hien co"* hoặc nút `d01`, tap ngay vào nút `Đăng nhập` để bung màn hình "Chào mừng bạn trở lại" (One-tap).
2. **Bẫy Đối Chiếu Tài Khoản Đã Có Sẵn Trong One-tap List**:
   - Trên màn hình "Chào mừng bạn trở lại", nếu tài khoản đích cần nuôi **đã có sẵn trong danh sách** (VD: `@thuthanh2911`, `@lamhongloan1907`), script phải **chạm trực tiếp vào tên tài khoản** để chuyển active session ngay lập tức mà không cần nhập pass/OTP (`already_logged_in`).
   - Chỉ khi nick đích **chưa có trong danh sách** mới tap *"Thêm tài khoản khác"* để vào form nhập email/pass.
3. **Bẫy `dismiss_profile_overlays` Tap Nhầm Nút `Đóng` (`z7l`) Do Regex Thông Báo Samsung**:
   - *Hiện tượng*: Trên Samsung Galaxy S7, thanh trạng thái có thông báo hệ thống: *"Tìm di động của bạn: Nếu bạn mất điện thoại thì sao?"*.
   - *Căn nguyên*: Trong `social_reg_v1.py`, hàm `dismiss_profile_overlays` có dòng `if any(k in flat for k in ["add phone", "them so dien thoai", "so dien thoai cua ban"]):`. Chuỗi `"so dien thoai cua ban"` sau khi `strip_accents` bị khớp dính chữ *"dien thoai cua ban"* trong thông báo Samsung! Script ngộ nhận là popup đòi thêm số điện thoại nên tap nút `Đóng` (`rid='com.ss.android.ugc.trill:id/z7l'`) ở góc trên phải, làm tắt mất màn hình "Chào mừng bạn trở lại"!
   - *Khắc phục*: Trong `dismiss_profile_overlays`, đặt ngay đầu hàm:
     ```python
     if any(k in flat for k in ["chao mung ban tro lai", "welcome back", "them tai khoan khac"]):
         return
     ```
     Bảo toàn tuyệt đối màn hình One-tap Login để luồng xử lý tài khoản tiếp quản.
