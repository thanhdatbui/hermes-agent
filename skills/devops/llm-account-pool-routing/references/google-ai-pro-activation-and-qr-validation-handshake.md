# Google AI Pro Link Activation & Antigravity QR Validation Handshake

## 1. Google AI Pro Subscription Link Activation Pitfalls
- **Short Link TTL (5-8 Minutes):** Các đường link nâng cấp Google AI Pro (thường từ các shop dịch vụ như SumiStore) có thời hạn bảo hành và hiệu lực kích hoạt rất ngắn (5–8 phút từ lúc sinh link).
- **Preflight GPM Session Validation Invariant:**
  - TUYỆT ĐỐI KHÔNG mở link kích hoạt trực tiếp nếu chưa kiểm tra GPM session còn sống (`one.google.com/home` hoặc `myaccount.google.com`).
  - Nếu profile bị văng đăng nhập hoặc dính checkpoint bảo mật (xác minh số điện thoại, email khôi phục), link nạp sẽ bị kẹt lại.
  - Khi ngâm link quá 8 phút, link sẽ bị server Google hủy hoặc đánh dấu đã sử dụng ("Gói thuê bao này đã được sử dụng"), dẫn đến mất trắng đơn hàng do người bán từ chối bảo hành.
- **Phân biệt "Tài khoản Pro rồi" của Shop vs Thực tế:**
  - Khi mở link quá hạn, Google One hiển thị thông báo "Gói thuê bao này đã được sử dụng". Người bán thường nhìn vào câu này và khẳng định tài khoản đã lên Pro.
  - BẮT BUỘC kiểm tra thực tế tại `one.google.com/home` hoặc `one.google.com/storage`:
    + Tài khoản thường (Free/Starter): Hiển thị "0% đã dùng (0 GB / 5 GB)" hoặc "15 GB", có nút "Nâng cấp" và mục "GOOGLE AI PRO" có biểu tượng Ổ KHÓA kèm nút "Đăng ký gói Google AI Pro".
    + Tài khoản Pro thật: Hiển thị "Bạn là thành viên gói Google AI Pro", dung lượng 5 TB hoặc 2 TB, nút "Chuyển đến Gemini".

---

## 2. Antigravity 403 VALIDATION_REQUIRED & Quota Refresh
- **Nguyên nhân Quota cũ:**
  - Tài khoản sau khi nâng cấp lên Google AI Pro, nếu token cũ trong OmniRoute (`storage.sqlite`) hoặc AGY CLI (`oauth_creds.json`) được cấp trước thời điểm nâng cấp, Google vẫn tính hạn mức Free cũ (`RESOURCE_EXHAUSTED 429: Individual quota reached`).
- **Bức tường xác minh Google (403 VALIDATION_REQUIRED):**
  - Khi gửi request mới qua OmniRoute / Antigravity để kích hoạt quota mới, Google sẽ chặn bằng lỗi:
    ```json
    403 PERMISSION_DENIED: "Verify your account to continue." (reason: "VALIDATION_REQUIRED")
    ```
  - Chi tiết lỗi đi kèm đường dẫn `validation_url`:
    `https://accounts.google.com/v3/signin/continue?plt=...&continue=https://developers.google.com/gemini-code-assist/auth/auth_success_gemini...`
  - Đường dẫn này dẫn thẳng tới trang quét mã QR:
    `https://accounts.google.com/v3/signin/challenge/iap/qrcode?TL=...`

---

## 3. Quy tắc "Giữ Trình Duyệt Mở" Trong Suốt Luồng Quét QR (Live Handshake Invariant)
- **CƠ CHẾ HOẠT ĐỘNG:**
  - Trang xác thực QR trên máy tính mở một kênh lắng nghe thời gian thực (WebSocket / long-polling) với server Google.
  - Khi người dùng dùng camera điện thoại quét mã QR và bấm "Xác nhận / Tiếp tục" trên thiết bị di động, server Google sẽ gửi tín hiệu handshake trả về phiên duyệt web đang mở trên máy tính để hoàn tất luồng OAuth và cấp quyền cho Antigravity.
- **CÁC SAI LẦM CHẾT NGƯỜI (CẤM):**
  1. **Đóng trình duyệt trước/trong khi quét:** Nếu tắt profile GPM hoặc đóng tab QR trên desktop sau khi chụp ảnh mã gửi người dùng, phiên kết nối bị đứt. Người dùng quét xong trên điện thoại nhưng desktop không nhận được tín hiệu $\rightarrow$ Google báo lỗi `500 That's an error` trên điện thoại và tài khoản vẫn bị kẹt 403 `VALIDATION_REQUIRED`.
  2. **Mở link `validation_url` trên máy khác:** Token `plt=...` gắn chặt với IP / fingerprint của phiên duyệt. Mở trên thiết bị khác (hoặc trên điện thoại không đăng nhập) sẽ báo lỗi `500 That's an error`.
- **QUY TRÌNH CHUẨN XÁC KHI XỬ LÝ LỖI QR VALIDATION:**
  1. Khởi động profile GPM của tài khoản trên máy tính qua API GPM v3 (`skip_proxy_check=true`).
  2. Dùng Playwright / CDP điều hướng tab tới `validation_url` để hiển thị trang QR `accounts.google.com/v3/signin/challenge/iap/qrcode`.
  3. Crop ảnh mã QR to, vuông vức, rõ nét (đảm bảo đầy đủ 3 góc định vị) và gửi cho người dùng qua Telegram.
  4. **BẮT BUỘC GIỮ NGUYÊN PROFILE GPM VÀ TAB QR MỞ TRỰC CHIẾN.** Không được đóng trình duyệt cho tới khi người dùng quét xong.
  5. Sau khi người dùng xác nhận đã quét, kiểm tra lại qua endpoint `POST /api/providers/<CONN_ID>/test` và gửi 1 request `pong` qua `v1/chat/completions` để nghiệm thu hạn mức Google AI Pro.
