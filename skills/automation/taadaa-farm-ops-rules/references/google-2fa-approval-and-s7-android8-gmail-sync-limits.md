# Quy trình Bật 2FA Google Authenticator & Đăng ký ChatGPT trên Samsung S7 (Android 8)

Ghi nhận ngày 19/09/2026 sau ca debug hiện trường trực tiếp trên farm máy Samsung S7 (Android 8).

---

## 1. Google 2FA Authenticator Setup: Bắt buộc bấm "Phê duyệt" (Approve)
### Hiện tượng
Sau khi thiết lập Authenticator bằng Playwright và nhập mã OTP 6 số thành công, Google hiển thị một hộp thoại bảo mật bổ sung:
> *"Phê duyệt trình xác thực này? ... Để đẩy nhanh quá trình này, bạn có thể phê duyệt trình xác thực mới bằng khóa truy cập hoặc khóa bảo mật hiện có."*
> Nút: `[Xóa]` và `[Phê duyệt]` (hoặc `[Delete]` và `[Approve]`).

### Nguyên tắc & Xử lý
- Popup này **chỉ xuất hiện một lần duy nhất** ngay sau khi vừa add trình xác thực. Nếu đóng tab hoặc bỏ qua, Google sẽ đưa trình xác thực vào diện chờ ngâm (quarantine/delay) trước khi cho phép dùng làm phương thức xác thực chính thức.
- **Kỷ luật Automation**: Trong script (`authenticator_flow.py`), ngay sau bước nhập OTP và bấm Xác minh, bắt buộc phải có bước `8b`:
  ```python
  try:
      approve_btn = page.locator('button:visible, [role="button"]:visible').filter(has_text=re.compile(r"phê duyệt|approve", re.I)).first
      if approve_btn.is_visible():
          approve_btn.click(force=True)
          time.sleep(3)
  except Exception as e:
      pass
  ```

---

## 2. ChatGPT Web trên Chrome Android S7: WebView mù DOM & Fallback Tọa độ Cookie
### Hiện tượng
Khi mở `https://chatgpt.com/auth/login?screen_hint=signup` trên Chrome Android (Samsung S7, độ phân giải 1080x1920):
- Chrome bọc toàn bộ nội dung web vào một khung `android.widget.FrameLayout (Lượt xem trên web)`.
- `uiautomator dump` **không bóc tách được DOM** bên trong WebView (cây XML chỉ có 21 nodes hệ thống, không có chữ "Chấp nhận tất cả" hay "Cookie").
- Script kiểm tra text trong XML sẽ bị mù hoàn toàn, dẫn đến treo timeout và văng lỗi `FAILED_AT_EMAIL_SUBMIT`.

### Giải pháp chuẩn
- Không phụ thuộc hoàn toàn vào XML dump. Nếu XML chỉ là `Lượt xem trên web` và chưa gõ email, tự động tap điểm fallback nút **`[Chấp nhận tất cả]`** trên màn hình 1080x1920:
  - Tọa độ nút `Chấp nhận tất cả`: `X=540, Y=1780`.
  - Tọa độ ô input `Email address`: `X=540, Y=1150`.
  - Tọa độ nút `Tiếp tục` (Continue): `X=540, Y=1485`.

---

## 3. App Gmail trên Samsung S7 (Android 8) bị Google chặn Push Sync
### Hiện tượng
Khi đăng ký tài khoản cần nhận OTP qua Gmail trên thiết bị Samsung S7:
- Mở app Gmail, màn hình đứng yên ở thông báo: *"Tài khoản chưa được đồng bộ hóa. Hãy nhấn [Đồng bộ ngay]..."*.
- Mở sang các máy khác chạy Android 8, app Gmail hiện cảnh báo hệ thống:
  > *"Hãy cập nhật thiết bị để đảm bảo an toàn: Để tiếp tục dùng ứng dụng Gmail và nhận các tính năng bảo mật mới nhất, hãy cập nhật hệ điều hành của thiết bị."*
- **Nguyên nhân cốt lõi**: Google đã ngừng hỗ trợ giao thức đồng bộ của app Gmail cũ trên hệ điều hành Android 8 (Oreo). Dù tài khoản Google hoàn toàn LIVE 100% và đã bật Auto-Sync trong Cài đặt hệ thống, app Gmail vẫn bị chặn kết nối ngầm kéo thư mới.

### Kỷ luật Vận hành Farm
- **Tuyệt đối không dùng app Gmail trên thiết bị Android 8 để chờ mã OTP**.
- **Giải pháp thay thế chuẩn**:
  1. **Đọc qua IMAP / Mail Web trên PC**: Chạy tool Playwright trên PC thông qua đúng Proxy di động của máy đó (`test.taadaa.click:51xx`) để truy cập web mail hoặc API trích xuất mã OTP.
  2. **Nạp profile vào GPMLogin trên PC**: Sau khi đã bật 2FA TOTP trên tài khoản, sử dụng profile GPM (trên nền Chromium hiện đại của PC) để lấy OAuth token nạp vào OmniRoute pool (`:20129`).
