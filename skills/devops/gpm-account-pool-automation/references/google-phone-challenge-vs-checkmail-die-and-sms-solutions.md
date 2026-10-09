# Google Phone Checkpoint (`challenge/iap`) vs Check-live DIE & Giải pháp SMS

## 1. Hiện tượng & Bản chất Kỹ thuật
Khi tài khoản Google bị gắn cờ bất thường (unusual activity) hoặc đợt quét OAuth security sweep:
- Sau khi nhập Mật khẩu + TOTP/OTP mail khôi phục thành công, Google chuyển hướng sang URL dạng `.../signin/v2/challenge/iap...` với thông báo:
  > *"Để giữ an toàn cho tài khoản của bạn, Google muốn đảm bảo rằng bạn chính là người đang cố đăng nhập. Nhập số điện thoại để nhận mã xác minh."*
- **Đối soát với tool Check-live (`checkmail.live` / `check_gmail_live_fast.py`):**
  - Tool check-live gửi probe xác thực hòm thư/tài khoản. Khi Google đưa tài khoản vào luồng Phone Challenge, quyền truy cập bình thường bị đình chỉ $\rightarrow$ Tool check-live phân loại ngay tài khoản là **`[die]`**.
  - **Bản chất thực tế phía Google:** Tài khoản **CHƯA BỊ XÓA** và **CHƯA BỊ DISABLE**. Ô nhập số điện thoại vẫn mở toang và sẵn sàng nhận mã SMS bất kỳ lúc nào để sống lại 100%.

## 2. Invariant Cooldown: Ngâm lâu có tự hết hỏi số không?
- **Kết luận từ dữ liệu Farm đối soát thực tế (tháng 09/2026):**
  - **100% các tài khoản dính `challenge/iap` để ngâm 1 tuần, 2 tuần hay cả tháng VẪN BẮT NHẬP SỐ.**
  - Không có trường hợp nào tự nhả (khác hoàn toàn với Rate Limit tạm thời theo IP).
  - Đây là cờ bảo mật cấp tài khoản (Account Security Flag) được lưu cứng trên máy chủ Google.

## 3. Cạm bẫy Hard-Lock khi thuê SIM / OTP dùng một lần
- Google hiển thị cảnh báo: *"Google will store this number and only use it for security purposes"*.
- **Nguy cơ mất acc vĩnh viễn (Hard-lock):**
  - Nếu dùng SIM thuê ảo dùng 1 lần (5sim, OTP bot chỉ tồn tại 10-15 phút), số này có thể bị Google gắn làm số điện thoại khôi phục (Recovery Phone).
  - Vài tuần hoặc vài tháng sau, nếu Google yêu cầu xác minh lại và chỉ định: *"Chúng tôi đã gửi mã xác minh tới số đuôi ••••••••846"* $\rightarrow$ Không còn giữ SIM để nhận code $\rightarrow$ **MẤT TÀI KHOẢN VĨNH VIỄN**.
- **Quy tắc Vàng cho Farm:**
  1. **Tài khoản tài sản / Cần giữ lâu dài:** BẮT BUỘC dùng **SIM vật lý thật của Farm** cắm máy nhận code. Một SIM thật có thể gỡ cho 4-5 tài khoản Gmail.
  2. **SIM ảo chỉ dùng cho tài khoản tiêu hao:** Khi chấp nhận tài khoản có thể bỏ nếu sau này bị hỏi lại đúng số cũ.
  3. **Trùng khớp Quốc gia:** Tài khoản chạy trên IP/Proxy Việt Nam (+84) **CẤM** thuê số nước ngoài (US, RU, ID, PH) để tránh kích hoạt cờ gian lận địa lý của Google.

## 4. Bảng giá & Đặc điểm các Sàn OTP (+84 Việt Nam) cho Google (Khảo sát 09/2026)
- **FastOTP.net:** ~964đ / SMS (rẻ nhất thị trường nội địa, nạp VNĐ qua Bank/MoMo, timeout 600s).
- **ViOTP.com:** ~1.500đ – 2.200đ / SMS (sàn lớn, kho SIM vật lý Viettel/Vina/Mobi mạnh, API RESTful chuẩn).
- **5sim.net (Lọc mạng Việt Nam):** ~$0.175 – $0.19 (~4.400đ – 4.800đ), chọn operator `virtual47` hoặc `virtual4`. Có cơ chế auto-refund nếu không về code sau 2 phút.
- **Rentcode.net:** ~2.000đ – 3.500đ / SMS.
- **Chothuesimcode.net:** ~$0.34 – $0.44 (~8.500đ – 11.000đ, kho 7/kho 8 khá đắt).
- **BinOTP.com:** Không cung cấp đầu số Việt Nam (chỉ có quốc tế).

## 5. Watchdog Fail-Safe Guard cho Phone Checkpoint
Trong bot/watchdog tự động hóa, khi phát hiện màn hình `challenge/iap`, BẮT BUỘC dừng ngay (Fail-Safe), không điền nhầm OTP mail khôi phục hay TOTP vào ô số điện thoại, ghi nhận failure category là `PHONE_CHECKPOINT` và cô lập tài khoản khỏi pool để bảo toàn tài sản.
