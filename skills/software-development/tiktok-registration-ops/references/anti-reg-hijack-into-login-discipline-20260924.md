# Chống Reg Hijack sang Login & Chống Nick Ký Sinh (2026-09-24)

## Bối cảnh & Rủi ro
Trong quá trình đăng ký tài khoản TikTok qua `social_reg_v1.py` trên farm:
- Nếu email nhập vào đã có tài khoản TikTok (`result == "registered"` hoặc `"registered_otp"`), runner cũ tự động nhảy vào nhập pass / đọc OTP và đăng nhập vào TikTok trên máy đang chạy reg.
- Rất nhiều trường hợp email này vốn dĩ thuộc quyền sở hữu của máy khác (đã lưu trong workbook tracking). Khi đăng nhập trên máy hiện tại, tài khoản đó trở thành "nick ký sinh" (parasite account), làm sai lệch mapping 1 máy - N tài khoản.

## Quy tắc bắt buộc
1. **Binding Preflight & Top-level Import**:
   Import `assert_account_machine_binding` ở top-level (CẤM import động bên trong hàm):
   ```python
   try:
       from .parasite_guard import assert_account_machine_binding, ParasiteAccountViolation
   except ImportError:
       from parasite_guard import assert_account_machine_binding, ParasiteAccountViolation
   ```
   Tại hàm `register()` trong `social_reg_v1.py`:
   ```python
   target_email = preferred_email or acc.get("email")
   if target_email:
       override = bool(acc.get("override_machine") or acc.get("allow_cross_machine"))
       try:
           assert_account_machine_binding(stt, target_email, allow_override=override, operator_reason="Canary reg")
       except ParasiteAccountViolation as pv:
           log(f"⚠ [PARASITE_BLOCKED] {pv}")
           dev_lease.release()
           return False
   ```
2. **CẤM HIJACK SANG LOGIN KHI PHÁT HIỆN EMAIL ĐÃ ĐĂNG KÝ**:
   Trong `pick_and_fill_email()`, khi `result in ("registered", "registered_otp")` hoặc fallback hints:
   - Ghi log: `log(f"   ✗ {em}: Email DA CO tai khoan TikTok tren he thong -> ABORT luong reg, cấm login len!")`
   - Chụp ảnh màn hình lưu lại bằng chứng.
   - Bỏ qua (`continue` để thử email khác) hoặc thoát / abort.
   - **TUYỆT ĐỐI CẤM** return `(em, pw, dob)` để đi tiếp vào flow login hay OTP trên luồng reg!

3. **Cạm Bẫy Đếm Số Lượng Nick Trên Switcher (TikTok v46+ & S7)**:
   Khi mở switcher để kiểm tra xem máy đã đủ 8 nick chưa trong `tap_add_account()`:
   Nút "Thêm tài khoản" dùng chung `resource-id` (`com.ss.android.ugc.trill:id/lli`) với tài khoản thật. BẮT BUỘC loại trừ nút này:
   ```python
   _acc_count = sum(
       1 for _n in _root.iter("node")
       if any(k in _n.attrib.get("resource-id", "") for k in ["n72", "lkp", "l9b", "lpw", "l_z", "lrq", "lli", "ndk"])
       and not any(x in (_n.attrib.get("text", "") + _n.attrib.get("content-desc", "")).lower() for x in ["thêm tài khoản", "add account", "add another"])
   )
   ```
   Nếu không lọc, máy có 7 nick + 1 nút thêm sẽ bị đếm nhầm thành 8 nick, văng lỗi `MACHINE_FULL_8_ACCOUNTS` oan.

4. **Sourcing Mail dongvanfb.net**:
   - CHỌN: **Loại 3 - ID 57 (350đ)**: Hotmail có Refresh Token Graph API full scope (`Mail.Read`, `Mail.ReadWrite`) + recovery mail `@fviainboxes.com` để ngâm 7 ngày đổi pass đá thiết bị cũ.
   - CẤM: **Loại 1 - ID 5**: Bị sàn bóp scope chỉ có IMAP/SMTP, thiếu `Mail.Read`, tool Farm gọi Graph API đọc OTP sẽ bị lỗi `Graph token invalid`.
