# So sánh cơ chế giải Captcha Audio (GPM Playwright) vs Fail-Fast (Android S7)

## 1. Cơ chế giải Audio Captcha trên GPM PC (`solve_recaptcha_audio`)
- **Môi trường**: Trình duyệt GPMLogin Chrome chạy trên PC Windows kết nối qua Playwright CDP.
- **Cách thức hoạt động**:
  1. Playwright truy cập trực tiếp vào cấu trúc DOM đa tầng và các `iframe` con (`enterprise/bframe`, `api2/anchor`).
  2. Bấm vào nút chiếc tai nghe (Audio Challenge button).
  3. Lấy trực tiếp đường link `src` file âm thanh `.mp3` từ thẻ `<audio>` hoặc `.rc-audiochallenge-tdownload-link`.
  4. Tải file về local, convert sang WAV qua `pydub`, gọi Google Speech Recognition (`speech_recognition` module) để giải mã chữ số/từ khóa.
  5. Điền kết quả vào `#audio-response` và bấm Submit.
- **Hiệu quả**: Tỷ lệ giải thành công cao (~85-90%) trên môi trường PC có đầy đủ quyền thao tác DOM Playwright.

---

## 2. Rào cản kỹ thuật khi cố giải Audio Captcha trên điện thoại S7 (Android)
1. **Rào cản Accessibility / ATX Agent (Thiếu quyền can thiệp DOM)**:
   - Trên S7, thao tác được điều khiển qua ADB và ATX Agent Accessibility (`dump_ui_hierarchy`).
   - Cửa sổ reCAPTCHA nằm sâu trong WebView của Chrome, ATX chỉ đọc được một khối WebView lớn (`android.webkit.WebView`) mà không xuyên sâu vào được các element bên trong iframe `bframe` của Google.
   - Không thể lấy được link `src` file MP3 qua lệnh ADB thông thường.
2. **Nguy cơ "Google Audio IP Lockout"**:
   - Google reCAPTCHA có cơ chế bảo vệ chống bot âm thanh tự động: khi phát hiện IP Proxy di động hoặc Proxy farm gửi truy vấn nghi vấn, nếu người dùng bấm vào biểu tượng tai nghe:
     > *"Máy tính hoặc mạng của bạn có thể đang gửi truy vấn tự động. Để bảo vệ người dùng, chúng tôi không thể xử lý yêu cầu âm thanh ngay lúc này."*
   - Một khi thông báo này xuất hiện, phương thức Audio bị khóa cứng 100%, việc cố giải sẽ gây timeout và treo máy.
3. **ADB Gesture Tracking**:
   - Khung reCAPTCHA trên Chrome Android theo dõi cử chỉ pointer touch. Thao tác ADB tap tức thời thường bị flag là bot và bị chuyển sang puzzle hình ảnh phức tạp (chọn xe buýt, vạch qua đường...).

---

## 3. Lý do áp dụng Fail-Fast Guard trên Android S7
1. **Bảo vệ mạng sống cho Gmail non trẻ**:
   - Khi dính reCAPTCHA mà cố gắng mò mẫm, tap bừa hoặc ngâm quá lâu, Google sẽ nâng mức độ nghi ngờ từ *Challenge* lên **Vô hiệu hóa tài khoản (DIE 100%)**.
   - Fail-Fast trong 0.5s: Chụp ảnh hiện trường $\rightarrow$ Đóng Chrome $\rightarrow$ Đưa máy về HOME giúp tài khoản Gmail không bị phạt nặng, vẫn LIVE trên thiết bị để ngâm tự nhiên.
2. **Tiết kiệm tài nguyên và thông luồng Farm**:
   - Một máy bị kẹt reCAPTCHA không được phép làm nghẽn tiến trình của 30-40 máy khác.
   - Trả về ngay `FAILED_AT_GOOGLE_RECAPTCHA` giúp hệ thống chuyển sang máy tiếp theo, giữ vững tiến độ của các ca nuôi feed và batch jobs.
3. **Phân định vai trò chuẩn**:
   - **Android S7**: Dùng luồng Direct Email OTP (nhập email $\rightarrow$ nhận mã 6 số về app Gmail $\rightarrow$ điền OTP). Luồng này sạch sẽ và né được 99% reCAPTCHA. Nếu gặp reCAPTCHA $\rightarrow$ Áp dụng **Fail-Fast**.
   - **GPM PC**: Dành cho các tài khoản sau khi đã ngâm đủ 7 ngày, có môi trường Playwright chuyên dụng để chạy `solve_recaptcha_audio`.
