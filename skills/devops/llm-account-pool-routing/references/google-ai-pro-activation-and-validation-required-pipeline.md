# Google AI Pro Upgrade: Post-Activation Validation Required & Link Burnout Pitfalls

## 1. Cơ Chế Bỏng Link Kích Hoạt (Activation Link Burnout & False "Already Used" Illusion)
- **Cơ chế thời hạn link:** Các link kích hoạt Google One / Google AI Pro từ shop (giá rẻ ~9k - 15k) thường có TTL rất ngắn và cam kết bảo hành trong vòng 5 - 8 phút từ lúc mua.
- **Rủi ro ngâm link do văng phiên / kẹt recovery:** Nếu profile GPM chưa được kiểm tra sống (preflight) mà đẩy link vào khi profile bị văng ra màn hình đăng nhập hoặc kẹt form xác minh email khôi phục (`m40_activated_proof.png`), link bị ngâm quá hạn 8 phút sẽ cháy.
- **Hiện tượng ngộ nhận "Đã kích hoạt Pro":**
  - Khi mở link quá hạn, trang Google One sẽ báo: *"Gói thuê bao này đã được sử dụng"* (This subscription has already been used).
  - Người bán (Seller) nhìn dòng chữ này sẽ lập tức quy kết là người mua đã bấm kích hoạt thành công cho tài khoản rồi (cộng thêm cớ quá 8 phút bảo hành để từ chối giải quyết).
  - **Kiểm chứng thực tế:** Bắt buộc mở trực tiếp `https://one.google.com/home` hoặc `https://one.google.com/storage` trên chính profile để kiểm chứng:
    - Nếu vẫn hiển thị dung lượng gốc `0 GB / 5 GB` (hoặc `15 GB`), có nút `Nâng cấp` và mục `GOOGLE AI PRO` vẫn có biểu tượng ổ khóa $\rightarrow$ Chứng minh 100% tài khoản chưa hề nhận gói Pro.

## 2. Quy Trình Sniper Chống Cháy Link
- Mở sẵn profile GPM và kiểm tra session sống (`one.google.com` hoặc `myaccount.google.com/family`) trước khi bắt đầu trực sniper.
- Ngay khi API báo `TELE_PRODUCT_PURCHASED`:
  - Trích xuất link kích hoạt (`subscription/new/...`).
  - Đẩy ngay qua CDP vào tab Chromium đang mở sẵn trong $\le 2$s.
  - Tự động bấm nút `Kích hoạt gói` trên trang đích Google One để hoàn tất nâng cấp ngay lập tức, triệt tiêu nguy cơ trễ hạn.

## 3. Lỗi 403 VALIDATION_REQUIRED & Hiện Tượng Quota 429 Ảo
### Triệu Chứng
- Tài khoản vừa kích hoạt Google AI Pro thành công (trên web báo *"Bạn là thành viên gói Google AI Pro"*).
- Khi đẩy vào OmniRoute / Antigravity CLI và gọi API upstream (`cloudcode-pa.googleapis.com`):
  - Upstream trả về HTTP 403:
    ```json
    {
      "error": {
        "code": 403,
        "message": "Verify your account to continue.",
        "status": "PERMISSION_DENIED",
        "details": [
          {
            "@type": "type.googleapis.com/google.rpc.ErrorInfo",
            "reason": "VALIDATION_REQUIRED",
            "metadata": {
              "validation_error_message": "Verify your account to continue.",
              "validation_url": "https://accounts.google.com/v3/signin/continue?plt=...&continue=...&flowName=GlifWebSignIn&authuser"
            }
          }
        ]
      }
    }
    ```
  - Khi chạy `agy cli ask` trên profile sandbox này, hệ thống sẽ báo:
    ```
    error: Individual quota reached. Please upgrade your subscription to increase your limits. (code 429)
    ```
  - **Bản chất:** Google chưa kích hoạt hạn mức Pro cho OAuth API token chừng nào tài khoản chưa giải quyết xong bức tường bảo mật `VALIDATION_REQUIRED`.

### Quy Trình Xử Lý
1. **Lấy `validation_url`:** Trích xuất từ log `omniroute-stdout.log` ngay sau khi request bị 403.
2. **Mở URL trong Profile GPM của tài khoản:** Điều hướng browser tới `validation_url`. Google sẽ hiển thị trang:
   - *"Xác minh thông tin để tiếp tục"*
   - Chế độ *"Quét mã QR bằng điện thoại"* (`accounts.google.com/v3/signin/challenge/iap/qrcode`).
3. **Chụp và Soi Mắt QR Code (Vision Invariant):**
   - Chụp toàn màn hình hoặc crop vùng mã QR.
   - Soi mắt kiểm tra trước khi gửi: Đảm bảo mã QR không bị lẹm góc, không bị popup che, đủ độ tương phản để camera quét được.
   - Đính kèm thẻ `MEDIA:<path>` gửi sang Telegram cho User quét camera trên điện thoại xác thực thiết bị.
4. **Hậu kiểm:** Sau khi User quét xong trên điện thoại, trang Google trên GPM tự động redirect về `auth_success_gemini` $\rightarrow$ Thử lại request qua OmniRoute/AGY CLI để nghiệm thu thông mạch.
