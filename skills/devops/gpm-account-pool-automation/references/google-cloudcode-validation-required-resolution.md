# Handling `VALIDATION_REQUIRED` (403 PERMISSION_DENIED) in Google Antigravity / Cloud Code via GPM

## 1. Bản chất sự cố & Cạm bẫy ngộ nhận Re-OAuth
- **Lỗi upstream:** Google Cloud Code API (`cloudcode-pa.googleapis.com` hoặc `daily-cloudcode-pa.googleapis.com`) trả về:
  ```json
  {
    "code": 403,
    "message": "Verify your account to continue.",
    "status": "PERMISSION_DENIED",
    "details": [{
      "reason": "VALIDATION_REQUIRED",
      "domain": "cloudcode-pa.googleapis.com",
      "metadata": {
        "validation_url": "https://accounts.google.com/v3/signin/continue?plt=...&continue=.../auth_success_gemini..."
      }
    }]
  }
  ```
- **CẠM BẪY NGHIÊM TRỌNG:** Nhầm lẫn giữa việc **chạy lại luồng OAuth** (cấp lại refresh token) và **gỡ cờ `VALIDATION_REQUIRED`**.
  - Re-OAuth chỉ làm mới access token/refresh token cho client (Code Assist). Nó **hoàn toàn KHÔNG gỡ bỏ được cờ chặn** ở tầng API upstream của Google.
  - Sau khi re-OAuth thành công 100%, gửi request vào model vẫn tiếp tục nhận 403 `VALIDATION_REQUIRED`.
  - **Ảo giác Quota Full 100%:** Khi Google chặn ở Gateway API (403), request không đi vào engine inference -> 0 token tiêu thụ -> Quota hiển thị 100% xanh tươi nhưng tài khoản thực chất đang chết (bị OmniRoute ngắt tạm thời).

## 2. Quy trình trích xuất mã QR / Link xác minh chuẩn xác qua GPM Profile
Không cần mở máy ảo VMware nếu GPM profile của tài khoản đó đã đăng nhập sẵn Google session sạch:
1. **Bắn 1 request cô lập để kích hoạt lỗi 403 tươi:**
   - Dùng `vm_rescue_lib.isolated_chat_test(conn_id, model="antigravity/claude-sonnet-4-6")` hoặc request trực tiếp có header `x-omniroute-connection: <conn_id>`.
2. **Trích xuất `validation_url` mới nhất:**
   - Đọc ngược từ cuối file log `omniroute-stdout.log` tìm chuỗi `"validation_url": "https://accounts.google.com/v3/signin/continue?plt=..."`.
   - Lưu ý unescape dấu gạch chéo `\/` -> `/`. Tham số `plt=...` là one-time token có thời hạn ngắn (1-2 phút).
3. **Mở GPM Profile tương ứng qua Playwright CDP:**
   - Gọi GPM API `/api/v3/profiles/start/<profile_id>?skip_proxy_check=true&win_scale=1.0`.
   - Kết nối Playwright `connect_over_cdp` vào địa chỉ `remote_debugging_address`.
   - Đặt viewport đủ lớn (`1280x900`) để QR code render rõ nét.
   - Điều hướng: `page.goto(validation_url, wait_until='domcontentloaded', timeout=30000)`.
   - Chờ 5s cho Google load trang `Xác minh thông tin để tiếp tục`.
4. **Chụp ảnh & Soi mắt kiểm tra trước khi gửi:**
   - Chụp `page.screenshot(path=..., full_page=True)`.
   - Soi mắt bằng vision xác nhận: Đúng tài khoản, có hiển thị mã QR nguyên vẹn rõ nét và link rút gọn `g.co/verify/...`.
   - **QUAN TRỌNG:** GIỮ NGUYÊN GPM profile đang mở (KHÔNG đóng lại) để khi user quét QR trên điện thoại, session trên máy tính nhận diện và hoàn tất đồng bộ ngay lập tức.
5. **Hướng dẫn User thao tác điện thoại:**
   - Bắt buộc quét bằng **Camera mặc định của điện thoại** (iPhone / Samsung).
   - **CẤM DÙNG APP ZALO** để quét (Zalo fail với các link xác thực bảo mật của Google).
6. **Hậu kiểm sau khi User quét xong:**
   - Chạy lại `isolated_chat_test` để xác nhận HTTP 200 OK trước khi đóng profile GPM.
