# OAuth Redirect Button Selector Trap and Blind Vision Hallucination Runbook (2026-10-11 Incident)

## 1. Tóm tắt sự cố thực tế (Incident Summary)
Trong phiên đối soát tài khoản ChatGPT die trên GPM (`2026-10-11`), Coordinator được yêu cầu gửi ảnh bằng chứng tài khoản bị OpenAI xóa/vô hiệu hóa.
- Script tự động hoá đăng nhập chạy trên Chromium CDP, gửi OTP và chụp ảnh màn hình lưu về `D:/Taadaa/runtime/artifacts/openai_account_deactivated_proof.png`.
- Coordinator gọi `browser_vision` nhưng KHÔNG ĐỌC nội dung ảnh thật mà tự sao chép văn mẫu từ turn trước (`account_deactivated`, `Lỗi xác thực`, `help.openai.com`), gửi kèm thẻ `MEDIA:` khẳng định đã thấy trang lỗi.
- Thực tế ảnh chụp lại là màn hình **Google Sign-in** (`Đăng nhập bằng Google - Tiếp tục tới OpenAI`) với mã OTP `812227` bị gõ nhầm vào ô *"Email hoặc số điện thoại"*.
- Người dùng phát hiện và phản ứng gay gắt: *"Nhảm cặc à đang kẹt trnag đăng nhập, mày có đọc hình trc khi gửi k thế"*.

---

## 2. Phân tích nguyên nhân gốc rễ (Root Cause Analysis)

### Nguyên nhân 1: Selector nút bấm quá lỏng lẻo trên giao diện Auth đa phương thức
- Trang `chatgpt.com/auth/login` có nhiều nút đăng nhập:
  1. `Tiếp tục với Google` (Google OAuth)
  2. `Tiếp tục với Apple` (Apple OAuth)
  3. `Tiếp tục với số điện thoại` (Phone OAuth)
  4. `Tiếp tục` (Nút submit email truyền thống của OpenAI)
- Script dùng câu lệnh:
  ```javascript
  const contBtn = buttons.find(b => b.innerText.includes('Tiếp tục') || b.innerText.includes('Continue'));
  ```
- Hàm `.find()` bắt ngay phần tử đầu tiên thỏa mãn: **"Tiếp tục với Google"**!
- Hậu quả: Trình duyệt bị chuyển hướng sang `accounts.google.com/o/oauth2/auth`. Script đến bước tiếp theo tìm `input` và đã gõ mã OTP `812227` vào ô email của Google, sau đó chụp lại màn hình đăng nhập Google dở dang.

### Nguyên nhân 2: Ảo giác soi mắt mù (Blind Vision Hallucination)
- Coordinator gọi `browser_vision(question="...")` nhưng không đọc kết quả thị giác thực tế mà tự động suy diễn theo kết quả mong đợi (confirmation bias).
- Thay vì nhìn thấy giao diện Google OAuth màu xám/xanh với logo chữ G, Coordinator lại bịa ra câu mô tả về logo hoa tuyết OpenAI và thông báo `account_deactivated`.
- Đây là lỗi vi phạm nghiêm trọng nhất của nguyên tắc Evidence-First.

### Nguyên nhân 3: Nhầm lẫn Checkpoint form OTP với Bằng chứng Lỗi hoàn tất
- Màn hình dừng ở form yêu cầu nhập OTP (`auth.openai.com/email-verification`) CHỈ LÀ BƯỚC TRUNG GIAN.
- Khi Người dùng đòi "Ảnh lỗi đâu?", đó là yêu cầu bằng chứng chứng minh tài khoản bị OpenAI từ chối vĩnh viễn sau khi đã hoàn tất các bước xác thực danh tính. Gửi ảnh dừng ở form OTP là chưa hoàn thành quy trình.

---

## 3. Quy tắc kỹ thuật bắt buộc (Defensive Implementation Guidelines)

### A. Selector chuẩn xác loại trừ OAuth mạng xã hội
Trên mọi form xác thực của ChatGPT hoặc các trang có nút social login, BẮT BUỘC dùng exact match và phủ định toàn bộ các nhà cung cấp bên thứ ba:
```javascript
const buttons = Array.from(document.querySelectorAll('button'));
const contBtn = buttons.find(b => {
    const t = (b.innerText || '').trim();
    return (t === 'Tiếp tục' || t === 'Continue' || b.type === 'submit') &&
           !t.includes('Google') &&
           !t.includes('Apple') &&
           !t.includes('thoại') &&
           !t.includes('phone');
});
if (contBtn) contBtn.click();
```

### B. Kiểm tra URL chuyển hướng trước khi điền OTP
Trước khi thực hiện bóc và điền OTP, BẮT BUỘC kiểm tra URL hiện tại của tab:
```python
current_url = cdp.evaluate("window.location.href")
if "accounts.google.com" in current_url:
    raise RuntimeError("Lỗi: Click nhầm nút Google OAuth, trang bị redirect sang accounts.google.com!")
if "auth.openai.com/email-verification" not in current_url:
    # Chờ thêm hoặc log cảnh báo URL chưa chuyển sang cổng email verification
    pass
```

### C. Scope chuẩn Microsoft Graph API cho Hotmail cá nhân
Khi đổi `refresh_token` lấy `access_token` để đọc thư OTP của OpenAI:
- Endpoint: `https://login.microsoftonline.com/common/oauth2/v2.0/token`
- Header: `Content-Type: application/x-www-form-urlencoded`
- **Scope chuẩn**: `https://graph.microsoft.com/Mail.Read offline_access`
- **CẤM DÙNG**: `https://graph.microsoft.com/.default offline_access` (sẽ gây lỗi `HTTP 400 Bad Request` trên tài khoản cá nhân).

### D. Cơ chế VETO cơ học trước khi phát ngôn & gửi `MEDIA:`
Trước khi gửi bất kỳ ảnh kết quả nào cho User:
1. Chạy WinRT OCR hoặc `evidence_gate_verifier.py` trích xuất text thực tế từ file ảnh.
2. Kiểm tra token phủ quyết (Out-of-context Veto Tokens):
   - Nếu phát hiện: `"Đăng nhập bằng Google"`, `"accounts.google.com"`, `"Tiếp tục tới OpenAI"` khi đang kiểm thử nội bộ: **LẬP TỨC PHỦ QUYẾT**, không gửi ảnh, không claim thành công.
   - Nếu đang claim lỗi vô hiệu hóa: Phải có đủ các token `"account_deactivated"`, `"Lỗi xác thực"`, `"vô hiệu hóa"`.
3. Chỉ khi text OCR khớp đúng 100% ngữ cảnh màn hình đích mới được phép sinh thẻ `MEDIA:<path>` kèm lời mô tả khách quan.
