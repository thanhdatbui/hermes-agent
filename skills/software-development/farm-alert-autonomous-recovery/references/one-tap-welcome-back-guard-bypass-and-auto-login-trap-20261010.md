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
3. **Cải tiến lâu dài cho Feed Runner (`feed_swipe_smoke.py`)**:
   - Khi `profile_preflight_identity_guard` phát hiện màn hình "Chào mừng bạn trở lại" (`is_welcome_back_screen`):
     * Nếu nick đích có trong One-tap list: Tap chọn nick đích để restore session.
     * Nếu nick đích không có trong One-tap list: Không dừng thẳng `manual-needed:login` mà gọi thẳng `_maybe_recover_missing_account_via_login(ctx, expected)`.
