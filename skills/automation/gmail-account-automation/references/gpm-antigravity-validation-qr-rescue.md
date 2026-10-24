# GPM Antigravity Validation Required & Device Verification QR Workflow

## Bối cảnh & Nguyên nhân lỗi
Tài khoản Google AI Pro (Antigravity) trong pool OmniRoute bị Google chặn ở tầng API upstream:
- **Lỗi upstream:** `HTTP 403 PERMISSION_DENIED`, reason `VALIDATION_REQUIRED`, domain `cloudcode-pa.googleapis.com`, message `"Verify your account to continue."`.
- **Ảo giác Quota 100%:** Khi Google chặn ngay tại gateway API upstream, không có request inference nào được chuyển tiếp vào mô hình -> 0 token được tiêu thụ -> Quota trên hệ thống Google vẫn nguyên vẹn 100%. Tuy nhiên OmniRoute sẽ gắn cờ ngắt model (con mắt gạch chéo) để bảo vệ pool.

## Bẫy sai lầm chết người (Pitfall)
- **TỰ CHẠY LẠI OAUTH KHÔNG GIẢI QUYẾT ĐƯỢC:** Chạy lại luồng cấp quyền OAuth Antigravity (`https://developers.google.com/gemini-code-assist/auth/auth_success_gemini`) qua GPM chỉ đổi Refresh Token mới. Nó **hoàn toàn không gỡ được cờ `VALIDATION_REQUIRED`** ở backend Google. Báo "thành công" sau OAuth là báo ảo.
- **Dán link xác minh vào trình duyệt ngoài:** Sẽ bị Google từ chối hoặc nhận nhầm account đang đăng nhập trên trình duyệt đó, không gỡ được cho account mục tiêu.

## Quy trình trích xuất mã QR và gỡ cờ chuẩn trên GPM
Khi cần gỡ cờ nhanh trực tiếp bằng Profile GPM của tài khoản:

### Bước 1: Trích xuất link `validation_url` tươi nhất từ API 403
Kích hoạt 1 request cô lập hoặc kiểm tra dòng lỗi `VALIDATION_REQUIRED` mới nhất trong log `C:/Users/Kibe/AppData/Roaming/omniroute/logs/omniroute-stdout.log` để lấy `validation_url`:
```json
"metadata": {
  "validation_url": "https://accounts.google.com/v3/signin/continue?plt=...&continue=https://developers.google.com/gemini-code-assist/auth/auth_success_gemini&sarp=1&scc=1&flowName=GlifWebSignIn&authuser"
}
```

### Bước 2: Bật GPM Profile và điều hướng vào `validation_url`
Khởi chạy GPM Profile tương ứng qua GPM Local API (`http://127.0.0.1:19995/api/v3/profiles/start/{id}`):
1. Kết nối qua Playwright CDP (`connect_over_cdp`).
2. Set viewport lớn (`width: 1280, height: 900`) để QR code hiển thị sắc nét.
3. Điều hướng `page.goto(val_url, wait_until='domcontentloaded')` và đợi 5 giây để Google render trang thử thách thiết bị (`uplevelingstep/selection`).
4. **BẮT BUỘC GIỮ PROFILE GPM MỞ:** Không được gọi close profile GPM ngay sau khi chụp ảnh. Google cần session trình duyệt máy tính duy trì kết nối WebSocket để nhận tín hiệu duyệt khi điện thoại quét QR thành công.

### Bước 3: Soi mắt kiểm tra & Gửi ảnh QR cho User quét
1. Chụp ảnh màn hình toàn trang (`page.screenshot(full_page=True)`).
2. Gọi `browser_vision` kiểm tra ảnh:
   - Xác nhận đúng tiêu đề: *"Xác minh thông tin để tiếp tục"*.
   - Đúng email tài khoản mục tiêu.
   - Mã QR góc phải rõ nét, không bị đen/che khuất.
3. Gửi ảnh `MEDIA:<path>` cho User:
   - Hướng dẫn dùng **Camera mặc định của điện thoại** (Samsung/iPhone) quét trực tiếp mã QR trên ảnh hoặc gõ link rút gọn `g.co/verify/...`.
   - **CẤM dùng app Zalo** quét mã vì Zalo fail với luồng Google Verification.

### Bước 4: Hậu kiểm cô lập (Verification)
Sau khi User quét xong trên điện thoại:
1. Chạy `isolated_chat_test` (tắt tạm thời các kết nối khác, ép test kết nối vừa cứu) với model `antigravity/gemini-3.8-flash-tiered`.
2. Kiểm tra kết quả trả về `status == 200` và `choices[0].message.content` có phản hồi.
3. Bật lại `is_active = 1` trong SQLite OmniRoute (`provider_connections`).
4. Đóng GPM Profile an toàn.
