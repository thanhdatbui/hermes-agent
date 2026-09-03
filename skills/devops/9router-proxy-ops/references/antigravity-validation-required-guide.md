# Antigravity VALIDATION_REQUIRED (Account Verification) Runbook

## 1. Triệu chứng (Symptoms)
- Dashboard 9Router / OmniRoute báo lỗi `403 Antigravity upstream error` hoặc hiển thị nhãn `insufficient_quota` / `model_not_found`.
- Gọi Provider Test / Connection Test vẫn **PASS / Active**, đọc được quota 100% hoặc danh sách model.
- Khi gửi prompt thực tế (`generateContent`) qua 9Router, Google trả về HTTP 403 kèm nội dung JSON:
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
          "domain": "cloudcode-pa.googleapis.com",
          "metadata": {
            "validation_url": "https://accounts.google.com/signin/continue?sarp=1&scc=1&continue=https://developers.google.com/gemini-code-assist/auth/auth_success_gemini&plt=..."
          }
        }
      ]
    }
  }
  ```

## 2. Nguyên nhân cốt lõi (Root Cause)
- Google Antigravity kích hoạt rào cản chống lạm dụng đối với tài khoản (thiếu Trust Score, nghi ngờ bot/proxy, hoặc tài khoản chưa xác minh danh tính qua thiết bị tin cậy).
- Token OAuth vẫn refresh được và đọc được quota, nhưng Google khóa cổng generate content cho đến khi người dùng vượt qua bước xác minh web (`GlifWebSignIn`).
- **Lưu ý quan trọng:** Google KHÔNG gửi mail cảnh báo về Gmail, KHÔNG hiện thông báo trên Google Account / Security Checkup thông thường. Link xác thực chỉ được sinh ra tạm thời trong trường `validation_url` của gói tin response lỗi 403.

## 3. Quy trình xử lý chuẩn (Resolution Protocol)

### Bước 1: Trích xuất `validation_url` tức thì
Khi phát hiện lỗi `VALIDATION_REQUIRED` / 403 từ Google Antigravity:
1. KHÔNG hướng dẫn user đi tìm trong Gmail hay cài đặt tài khoản Google thông thường.
2. KHÔNG tự ý reset quota, xóa account hay can thiệp database.
3. Chạy script hoặc cào ngay raw error response JSON từ endpoint 9Router để lấy chính xác trường `validation_url` (chứa token phiên `plt=...`).

### Bước 2: Gửi link cho User xác minh
1. Cung cấp ngay link `validation_url` cho user.
2. Hướng dẫn user mở trình duyệt đang đăng nhập đúng tài khoản Google bị khóa.
3. User hoàn tất các bước trên màn hình (nhận diện thiết bị / số điện thoại / CAPTCHA).
4. Màn hình xác nhận thành công chuyển hướng về `developers.google.com/.../auth_success_gemini`.

### Bước 3: Reconnect trong 9Router
1. Sau khi user xác minh thành công, mở dashboard 9Router (`/dashboard/providers/antigravity`).
2. Bấm **Reconnect / Test Connection** tại dòng tài khoản đó để làm mới token OAuth.
3. Gửi test request generateContent để xác nhận thông luồng.
