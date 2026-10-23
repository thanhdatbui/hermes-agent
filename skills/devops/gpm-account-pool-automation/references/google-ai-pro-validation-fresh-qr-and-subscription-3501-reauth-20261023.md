# Quy Trình Tạo Link QR Validation Tươi (Fresh PLT) & Khắc Phục Lỗi 403 SUBSCRIPTION_REQUIRED (#3501) Sau Khi Quét QR (2026-10-23)

## 1. Cơ Chế Hết Hạn Của Mã QR Xác Minh (Short TTL ~120s)
- **Hiện tượng:** Khi tài khoản vừa nâng cấp Google AI Pro bị Google Cloud Code chặn lỗi 403 `VALIDATION_REQUIRED`, `validation_url` chứa tham số `plt=...` chỉ có hiệu lực trong khoảng 1–2 phút.
- **Hậu quả:** Nếu người dùng quét chậm hoặc yêu cầu "mở lại link đi", việc mở lại URL cũ sẽ bị Google từ chối với thông báo:
  *"Bạn chưa đăng nhập. Phiên của bạn đã kết thúc vì không có hoạt động. Hãy thử đăng nhập lại."*
- **Quy trình kích hoạt Fresh `validation_url` tức thì (Zero-VM, Zero-Manual):**
  Không cần khởi động máy ảo hay chờ đợi lâu. Gửi 1 POST request cô lập trực tiếp tới endpoint Google Cloud Code với `access_token` của tài khoản qua đúng proxy mobile tương ứng:
  ```python
  import json, urllib.request

  url = 'https://daily-cloudcode-pa.googleapis.com/v1internal:streamGenerateContent?alt=sse'
  headers = {
      'Authorization': f'Bearer {token}',
      'Content-Type': 'application/json'
  }
  payload = json.dumps({
      'project': 'aicode-consumers',
      'model': 'claude-sonnet-4-6',
      'request': {
          'contents': [{'role': 'user', 'parts': [{'text': 'hi'}]}]
      }
  }).encode('utf-8')

  proxy_handler = urllib.request.ProxyHandler({'http': proxy_url, 'https': proxy_url})
  opener = urllib.request.build_opener(proxy_handler)
  req = urllib.request.Request(url, data=payload, headers=headers, method='POST')
  try:
      with opener.open(req, timeout=15) as resp:
          pass
  except urllib.error.HTTPError as e:
      body = json.loads(e.read().decode('utf-8'))
      for detail in body.get('error', {}).get('details', []):
          meta = detail.get('metadata', {})
          if 'validation_url' in meta:
              fresh_url = meta['validation_url']
  ```
  Ngay lập tức, điều hướng GPM profile đến `fresh_url` để hiển thị mã QR mới tinh cho người dùng quét.

---

## 2. Cạm Bẫy Lỗi 403 SUBSCRIPTION_REQUIRED (#3501) Sau Khi Quét QR Thành Công
- **Hiện tượng:** Người dùng dùng camera điện thoại quét mã QR thành công, màn hình trên trình duyệt GPM chuyển sang:
  `https://developers.google.com/gemini-code-assist/auth/auth_success_gemini` (*"Authentication successful | Gemini Code Assist"*).
  Tuy nhiên, khi gửi request vào model, Google Cloud Code API vẫn trả về:
  ```json
  {
    "error": {
      "code": 403,
      "message": "You do not have a valid license of this product. Please contact your administrator to request a license... (#3501)",
      "status": "PERMISSION_DENIED",
      "details": [{
        "reason": "SUBSCRIPTION_REQUIRED"
      }]
    }
  }
  ```
- **Nguyên nhân gốc rễ (Root Cause):**
  - Mặc dù thiết bị đã vượt qua thử thách QR, Access Token và Refresh Token hiện tại đang lưu trong OmniRoute và AGY sandbox được cấp từ trước khi tài khoản được nâng cấp Google One Pro (vẫn mang claim gói Free/Starter).
  - Tầng Gateway của Google Cloud Code kiểm tra claim trong token thấy không có license Pro nên ném mã lỗi `#3501`.

---

## 3. Quy Trình Khắc Phục Triệt Để: Re-OAuth Đổi Token Pro Mới Tinh
Ngay sau khi trang cán đích `auth_success_gemini`, bắt buộc thực hiện ngay chu trình Re-OAuth trên profile GPM:
1. **Khởi tạo luồng OAuth từ OmniRoute:**
   - Gọi `GET http://127.0.0.1:20129/api/oauth/antigravity/authorize?redirect_uri=http://127.0.0.1:20129/callback`
   - Lấy `authUrl`, `codeVerifier`, `state`.
2. **Điều hướng trên Profile GPM đang mở:**
   - Điều hướng `page.goto(authUrl)`.
   - Vì session Google và thiết bị vừa được xác thực hợp lệ, Google hiển thị Account Chooser: tự động click chọn email mục tiêu (tọa độ `(750, 360)` hoặc `div[role="link"]`).
   - Tự động click bypass nút cảnh báo `"Đăng nhập"` / `"Sign in"`.
   - Bắt Authorization Code từ URL chuyển hướng `/callback?code=4/0AX...`.
3. **Đổi Token mới qua OmniRoute Exchange API:**
   - Gửi payload `{"code": code, "redirectUri": redirect_uri, "codeVerifier": code_verifier, "state": state}` tới `POST http://127.0.0.1:20129/api/oauth/antigravity/exchange`.
   - Nhận phản hồi `{"success": true}` (HTTP 200).
4. **Đồng bộ Dual-Pool & Kiểm Chứng Nghiệm Thu:**
   - Chạy `python D:/Taadaa/tools/setup_agy_profile_creds.py` để ghi token Pro mới vào `.gemini/` của AGY sandbox.
   - Chạy `vm_rescue_lib.isolated_chat_test(connection_id)`:
     * Request trả về `status: 200` và `content: "OK"`.
     * Đối soát SQLite `call_logs` xác nhận `status = 200` và `error_summary IS NULL`.
5. **Dọn dẹp:**
   - Gọi GPM API `/api/v3/profiles/stop/{id}` để đóng profile nhẹ nhàng, giải phóng RAM.
