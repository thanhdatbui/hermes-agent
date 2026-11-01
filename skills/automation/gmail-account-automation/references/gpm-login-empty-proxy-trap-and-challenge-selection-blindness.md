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

## 4. BẪY SOI NHẦM SQLITE GPM DB VS GPM REST API (CHỐNG PHÁN ẨU BÁO ĐỘNG GIẢ)
- **Cạm bẫy thực tế**: Soi trực tiếp trường `JsonData` trong SQLite `profile_data.db` thấy `proxy: None, raw_proxy: None` -> vội vã phán ẩu "toàn bộ profile không có proxy" làm User nổi giận và hoang mang tột độ.
- **Sự thật kiến trúc GPM**:
  * GPMLogin v3 quản lý cấu hình proxy qua backend C#; trường `raw_proxy` được trả về chính xác 100% qua endpoint REST API: `http://127.0.0.1:19995/api/v3/profiles`.
  * Trên thực tế, các profile farm (`M19 - 5123 - luunhu`, `M49 - 5113 - cathoa`) đã được cấu hình proxy 4G đầy đủ từ trước qua API (`test.taadaa.click:5123`, `5113`).
- **Kỷ luật bất biến**: CẤM kết luận về proxy hoặc trạng thái profile GPM chỉ bằng cách select thô SQLite. BẮT BUỘC xác minh qua GPM Local API (:19995) hoặc chạy probe curl/urllib trước khi đưa ra nhận định.

## 5. GIẢI PHÁP L2-SURGERY CHO CHALLENGE SELECTION TRONG RUN_OAUTH_S7_PIPELINE
- Trong `scripts/run_oauth_s7_pipeline.py`:
  * Mở rộng `classify_s7_challenge_selection`: thêm tham số `has_recovery: bool = False`, gán `("RECOVERY_EMAIL", has_recovery)` vào danh sách ưu tiên ngay sau `TOTP`.
  * Mở rộng `detect_challenge_options`: thêm `has_recovery: bool = False`, bắt locator `div[data-challengetype="4"], div[data-challengetype="2"], li:has-text("khôi phục"), li:has-text("recovery")`.
  * Tại điểm gọi login loop (`run_oauth_pipeline`): truyền `has_recovery=bool(recovery)` để script tự động click chọn email khôi phục khi Google đưa ra danh sách phương thức xác minh.
