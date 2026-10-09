# Bắt nhầm Secret Key "GALAXYESSENTIALS" từ Samsung Launcher & Kẹt Nút Chuyển OTP (2026-09-07)

## 1. Hiện tượng & Triệu chứng lỗi (Alert)
- Khi chạy Add 2FA live trên các thiết bị Samsung Galaxy S7 (ví dụ Máy 1, Máy 2), runner văng lỗi:
  `2FA Failed: OTP_ADVANCE_BUTTON_NOT_REACHED (attempts=3)`
- Dù runner báo đã bắt được Secret Key 16 ký tự và lưu vào DPAPI Journal (`state=CAPTURED`), máy không chuyển được sang màn nhập OTP và văng lỗi sau 4 lần swipe tìm nút "Tiếp".
- Rerun hoặc retry các attempts tiếp theo đều lập tức fail lại lỗi trên.

## 2. Nguyên nhân cốt lõi (Root Cause)
1. **Lọc Base32 thiếu ràng buộc package:**
   - Trong `python_runner/core/ui_interact.py`, `_base32_candidates()` quét chuỗi có độ dài 16-64 ký tự thỏa mãn regex `[A-Z2-7]+` và thử `generate_totp(compact, timestamp=0)`.
   - Trên màn hình chính Launcher Samsung S7 (`com.sec.android.app.launcher`), có widget / icon mang tên `"Galaxy Essentials"` (chuỗi compact `"GALAXYESSENTIALS"` dài đúng 16 ký tự).
   - Tất cả các ký tự `G, A, L, X, Y, E, S, N, T, I` ngẫu nhiên đều thuộc bảng mã RFC 4648 Base32 (không chứa 0, 1, 8, 9).
   - `generate_totp("GALAXYESSENTIALS", 0)` sinh mã thành công mà không văng ngoại lệ.
2. **Kích hoạt Resume giả mạo trong `navigate_and_verify_account()`:**
   - Khi `run_capture_phase_b.py` khởi động, điện thoại đang ở màn hình Launcher.
   - `navigate_and_verify_account()` gọi `read_secret_node(current)` để kiểm tra nếu màn hình đang ở sẵn bước hiển thị Secret Key thì resume tiếp.
   - Do không lọc package, hàm quét trúng widget `"GALAXYESSENTIALS"` trên launcher, nhận diện là secret hợp lệ và gán `self._resume_key_screen = True`.
   - Runner tưởng đã ở màn hình Authenticator Setup nên **bỏ qua hoàn toàn** việc mở app TikTok, bỏ qua kiểm tra tài khoản, bỏ qua vào Settings/Bảo mật.
3. **Kẹt Journal CAPTURED & Lỗi nút chuyển bước:**
   - Runner lưu `"GALAXYESSENTIALS"` vào Journal DPAPI với state `CAPTURED`.
   - Tiếp đó, runner gọi `advance_to_otp()` để tìm nút "Tiếp" / "Tiếp tục" ngay trên... màn hình chính Launcher Samsung.
   - Màn hình launcher không có nút này, adapter thử vuốt 4 lần rồi ném `LiveAdapterError("OTP_ADVANCE_BUTTON_NOT_REACHED")`.
   - Ở mọi lần retry/rerun sau, `execute_phase_b` thấy journal đã ở state `CAPTURED` nên lại tiếp tục nhảy cóc vào `advance_to_otp()` trên launcher và văng lỗi lặp lại.

## 3. Quy trình khắc phục chuẩn (Fix & Hardening)
1. **Hardening `read_secret_node()` & `_base32_candidates()`:**
   - Chỉ quét các UIElement có `element.attrib.get("package") == "com.ss.android.ugc.trill"`.
   - Tuyệt đối bỏ qua các package hệ thống `com.sec.*`, `com.android.*`.
   - Thêm blacklist chuỗi tĩnh đã biết: `compact != "GALAXYESSENTIALS"`.
   - Trong `read_secret_node()`: nếu XML hierarchy không chứa package TikTok, raise `UIInteractError("current UI is not TikTok")`.
2. **Hardening `navigate_and_verify_account()`:**
   - Chỉ gọi `read_secret_node(current)` khi `current` thuộc TikTok (`"com.ss.android.ugc.trill" in current`). Nếu đang ở launcher, bắt buộc điều hướng mở TikTok và về Profile.
3. **Mở rộng nhận diện nút chuyển bước trong `advance_to_otp()`:**
   - TikTok build thực tế dùng nhãn `"Tiếp tục"` (hoặc `"Next"`), code cũ tìm `"Tiếp"` với `prefix=False` sẽ fail.
   - Duyệt candidates: `["Tiếp tục", "Tiếp", "Next", "Continue"]`, tối ưu dump UI 1 lần mỗi chu kỳ cuộn.
   - Bổ sung fallback tìm node `android.widget.Button` hoặc clickable ở nửa dưới màn hình sau dòng Secret Key.
4. **Purge Journal lỗi:**
   - Khi phát hiện máy bị kẹt state `CAPTURED` với secret giả, phải xóa hoặc purge file `.dpapi` trong `journals/` của host (sử dụng `JournalStore.purge(account_hash)`) trước khi rerun để máy thực hiện lại từ đầu.
