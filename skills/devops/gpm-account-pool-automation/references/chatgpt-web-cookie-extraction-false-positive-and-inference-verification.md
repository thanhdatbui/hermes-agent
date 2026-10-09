# ChatGPT-Web Cookie Extraction False-Positive & Mandatory Inference Verification (2026-09-30)

## 1. Bối cảnh & Sự cố thực tế

Trong đợt chạy giải cứu hàng loạt tài khoản ChatGPT Web Pool trên GPMLogin, script tự động báo "Thành công 100%" và gửi ảnh screenshot nghiệm thu cho User. Tuy nhiên khi User mở ảnh kiểm tra, phát hiện toàn bộ các màn hình đều đang ở trạng thái:
- *"Your session has expired ... Log in"* (Phiên đã hết hạn).
- *"Tiếp tục với Apple / Số điện thoại / Email"* (Màn hình đăng nhập khách).
- Modal overlay che khuất: `data-octane-static-cookie-consent` hoặc `modal-no-auth-login`.

Đây là sự cố **BÁO DONE KHÔNG CÓ BẰNG CHỨNG (FALSE SUCCESS)** nghiêm trọng nhất trong vận hành tự động hóa.

---

## 2. Ba cái bẫy kỹ thuật chết người (Root Cause)

### Bẫy 1: URL Đăng Xuất giống hệt URL Đăng Nhập
- Khi điều hướng tới `https://chatgpt.com/`, dù tài khoản đang đăng nhập hay đã bị văng session (logged out), thanh địa chỉ trình duyệt **VẪN LÀ `https://chatgpt.com/`** (hoàn toàn không có path `/auth/`).
- Bất kỳ đoạn code nào kiểm tra:
  ```python
  # SAI LẦM NGHIÊM TRỌNG:
  if "chatgpt.com" in page.url and "/auth/" not in page.url:
      # Tưởng nhầm là đã đăng nhập thành công!
  ```
  sẽ bị lừa 100% khi gặp màn hình khách hoặc màn hình "Your session has expired".

### Bẫy 2: Cookie Jar lưu trữ Cookie cũ hết hạn
- Trong Chrome Profile của GPM, cookie `__Secure-next-auth.session-token` từ các phiên đăng nhập trước đó vẫn được lưu trữ trên đĩa trong file SQLite `Cookies` của trình duyệt.
- Khi gọi `context.cookies(["https://chatgpt.com"])`, Playwright bốc ra chuỗi cookie cũ bắt đầu bằng `eyJhbG...` (dù token này đã bị OpenAI thu hồi/hết hạn trên server).
- Script kiểm tra `if token.startswith("eyJhbG"): return token` sẽ lấy đúng chuỗi rác đã chết, nạp vào OmniRoute DB và ngộ nhận là tài khoản đã hồi sinh.

### Bẫy 3: Đánh đồng phương thức đăng nhập (Google SSO vs ID/Pass)
- Farm có 2 nhóm tài khoản ChatGPT:
  1. Nhóm tài khoản cũ: Đăng ký qua Google SSO (`Continue with Google`).
  2. Nhóm tài khoản mới: Đăng ký trực tiếp bằng Email + Password (`chatgpt_gpm_direct_reg.py` — 100% Direct Email + Pass).
- Khi script mặc định chỉ đi tìm nút `Continue with Google`:
  - Với acc ID/Pass, luồng Google SSO không đăng nhập được vào ChatGPT.
  - Các nút đăng nhập bị chặn bởi modal consent (`data-octane-static-cookie-consent`) gây timeout 30s.

---

## 3. Quy chuẩn phòng ngừa & Khắc phục bắt buộc

### Quy tắc 1: OCR Readback & UI Marker Validation
Trước khi trích xuất cookie, bắt buộc phải kiểm tra DOM hoặc chạy OCR xác nhận không có các chuỗi lỗi:
- CẤM có: `"Your session has expired"`, `"Phiên của bạn đã kết thúc"`, `"Log in"`, `"Đăng nhập"`, `"Sign up"`, `"Đăng ký"`.
- BẮT BUỘC có: Input textarea chat (`#prompt-textarea` hoặc `div[contenteditable="true"]`) hoặc menu user profile.

### Quy tắc 2: Mandatory Live Inference Probe (Thẩm định bằng thực thi)
TUYỆT ĐỐI CẤM gán `is_active = 1` hay `test_status = 'active'` chỉ dựa vào việc bóc tách chuỗi cookie.
Bắt buộc phải thực hiện 1 request HTTP thử nghiệm trực tiếp qua OmniRoute (:20129):
```python
req_body = {
    'model': 'chatgpt-web/gpt-5.6-sol-high',
    'messages': [{'role': 'user', 'content': '1+1=? Trả lời đúng 1 số.'}],
    'max_tokens': 5
}
# Chỉ khi nhận HTTP 200 và content chứa "2" mới được ghi nhận connection LIVE!
```

### Kết quả đối soát thực tế đo được sau khi thẩm định động:
- Trong 31 connections nạp vào OmniRoute:
  - **18 tài khoản LIVE THẬT** (phản hồi trong 9s – 18s).
  - **13 tài khoản VĂNG SESSION THẬT** (dính 401 do cookie cũ hết hạn).
- Đã lập tức deactivate 13 tài khoản chết (`is_active = 0`, `test_status = 'banned'`) để bảo vệ combo `gpt-web-sol` hoạt động trơn tru.
