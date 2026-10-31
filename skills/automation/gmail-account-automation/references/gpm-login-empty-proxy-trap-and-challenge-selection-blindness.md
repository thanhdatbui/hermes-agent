# GPM Login: Empty Proxy Trap, Challenge Selection Blindness & Anti-Band-Aid Triage

## 1. BẪY PROFILE RỖNG PROXY (EMPTY PROXY TRAP GÂY HARD PHONE CHECKPOINT)
- **Hiện tượng**: Tài khoản Gmail trust cao (đã bật 2FA, có mail khôi phục, nuôi lâu trên phone farm S7) bỗng nhiên bị fail đăng nhập liên tục trên GPM, bị Google chặn ở màn hình `challenge/iap` (ép xác minh số điện thoại mới) và bắn email cảnh báo an ninh dồn dập về Gmail chính chủ của User.
- **Nguyên nhân gốc rễ**:
  * Profile trong GPM DB (`profile_data.db`) có `proxy: None, raw_proxy: None`.
  * Khi watchdog hoặc launcher khởi động profile (`/profiles/start/{id}`), Chromium mở bằng IP mạng trực tiếp của PC (Fixed Broadband).
  * Google phát hiện tài khoản vốn hoạt động trên IP di động 4G (MobiProxy farm) đột ngột xuất hiện trên IP desktop lạ kèm header automation -> Google kích hoạt Identity Action Point (`challenge/iap`) và bắn security alert.
- **Bẫy trong script chuẩn hóa (`normalize_gpm_proxies.py`)**:
  * Hàm `is_proxy_needing_normalization(raw_proxy)` kiểm tra `if not raw_proxy: return False` -> **bỏ qua hoàn toàn các profile chưa có proxy**!
  * Khắc phục: Phải bắt buộc phát hiện cả trường hợp `raw_proxy is None or raw_proxy == ""` để tự động nạp proxy chuẩn từ `PROXYgandienthoai.xlsx` theo số máy (`mid`).

## 2. BỆNH MÙ "EMAIL KHÔI PHỤC" TRONG CHALLENGE SELECTION
- **Hiện tượng**: Script có sẵn password, recovery email (`col 3` Excel) và 2FA Authenticator secret (`col 4` Excel), nhưng khi login vẫn văng `PHONE_CHECKPOINT`.
- **Nguyên nhân gốc rễ**:
  * Trong bộ chọn phương thức `classify_s7_challenge_selection` và `detect_challenge_options`, script chỉ định nghĩa: `TOTP`, `PROMPT`, `S7_SECURITY_CODE`, `FARM_SMS`, `PHONE24_SMS`.
  * **HOÀN TOÀN THIẾU `RECOVERY_EMAIL`**! Khi Google đưa ra danh sách chọn cách xác minh ("Nhận mã xác minh tại email khôi phục" hoặc "Xác nhận email khôi phục"), script bị mù, không click chọn option này.
  * Selector TOTP tiếng Việt bị trượt: Khi Google hiển thị tiếng Việt ("Ứng dụng xác thực"), selector tìm `li:has-text("Authenticator")` bị miss, khiến script bỏ qua TOTP dù có secret key `pyotp`.
  * Script bấm "Thử cách khác" đúng 1 lần; nếu màn hình chưa chuyển ngay thì ở nhịp sau lập tức coi là `PHONE_CHECKPOINT` và bỏ cuộc.

## 3. KỶ LUẬT ĐIỀU TRA CHỐNG LÀM ĐỐI PHÓ (ANTI-BAND-AID INVARIANT)
- **CẤM TUYỆT ĐỐI**: Khi tài khoản có đầy đủ thông tin (pass, mail kp, 2FA) mà fail liên tục, cấm Coordinator vội vã đưa vào blacklist/quarantine rồi báo cáo "đã xử lý xong".
- **Phân biệt rạch ròi**:
  * *Quarantine/Cooldown*: Chỉ là biện pháp cầm máu tạm thời để ngăn spam alert về máy User.
  * *Phẫu thuật gốc rễ*: BẮT BUỘC kiểm tra (1) Profile GPM có bị rỗng proxy không, (2) Script login có nạp đúng credentials không, (3) DOM challenge có bị nuốt option Email khôi phục / TOTP không.
