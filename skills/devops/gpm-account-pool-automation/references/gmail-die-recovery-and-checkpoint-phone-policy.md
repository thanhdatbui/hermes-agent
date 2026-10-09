# Quy trình cứu & Quản lý Gmail DIE / Checkpoint / SMS Verification

## 1. Nguyên tắc cốt lõi: CẤM TỰ Ý XÓA PROFILE GPM KHI GMAIL DIE
- **Lý do**: Profile GPM của tài khoản Gmail có thể đã được nạp tiền thuê SIM (5sim / SMS OTP) để đăng ký OpenAI / ChatGPT / Codex hoặc lưu session làm việc quan trọng.
- Khi Gmail bị Google vô hiệu hoá hoặc dính checkpoint:
  - **Tài khoản OpenAI / Codex đăng nhập độc lập**: Vẫn đăng nhập bình thường bằng Email + Password riêng (CẤM dùng Google SSO).
  - Nếu tự động gọi API `profiles/delete/{id}` xóa profile GPM, toàn bộ cookie, token, và tài khoản OpenAI/Codex đã tốn chi phí ver số sẽ bị mất trắng.
  - Trong script vòng đời (`sync_gpm_lifecycle.py`), BẮT BUỘC bỏ qua lệnh xóa profile DIE.

---

## 2. Quản lý dữ liệu Excel: Tách biệt Sheet DIE Archive & Cột ChatGPT_Reg
- Sổ cái Master: `master_gmail_manager.xlsx`.
- **Sheet `Master_All` và các sheet vận hành (`Gmail_Dat`, `Kibe_Farm_S7`, `Admin_GPM_Pool`)**:
  - CHỈ chứa các tài khoản `LIVE` sạch 100% để phân bổ máy và chạy automation không bị lỗi.
- **Sheet `Gmail_DIE_Archive`**:
  - Gom toàn bộ tài khoản `DIE`, `COOLDOWN_PHONE` vào một nơi riêng biệt.
  - Giữ nguyên toàn bộ thông tin: `Email`, `Password`, `Recovery_Email`, `2FA_Secret`, `SDT` (đã thuê SIM), `Proxy`, `Tên Profile GPM`, `Ghi chú`.
- **Cột chuẩn hóa `ChatGPT_Reg`**:
  - Hiện diện trên tất cả các sheet ngay sau cột `Trạng Thái`.
  - Đánh dấu giá trị `CHATGPT_READY` hoặc để trống để lọc tức thì tài khoản đã tạo OpenAI/Codex.

---

## 3. Phân loại Checkpoint Google khi đăng nhập lại Gmail DIE
Khi điều hướng đến `https://accounts.google.com/ServiceLogin` qua Playwright CDP:

| Dạng thông báo Google | Bản chất kỹ thuật | Hướng xử lý |
| :--- | :--- | :--- |
| **"Không tìm thấy tài khoản này"** (`Couldn't find your Google account`) | Tài khoản đã bị Google xóa sổ vĩnh viễn (Purged). | Không cứu được Gmail. Lưu ý kiểm tra auth ChatGPT độc lập. |
| **"Xác nhận số điện thoại khôi phục của bạn"** | Google KHÔNG gửi OTP, chỉ dùng số cũ làm câu hỏi bảo mật (Security Challenge). | Lấy đúng số điện thoại cũ đã lưu trong `Gmail_DIE_Archive` (cột SDT) điền vào -> Google cho qua 100%. |
| **"Nhập một số điện thoại để nhận mã xác minh"** | Anti-bot checkpoint (không bắt buộc số cũ). | Mua số ảo mới (5sim / SMS service) dán vào nhận OTP để mở khóa. |
| **"Mật khẩu của bạn đã thay đổi N tháng trước"** | Mật khẩu trong Excel là mật khẩu cũ. | Cần cập nhật mật khẩu mới nhất. |
| **"Bạn đã thử xác minh quá nhiều lần"** (Rate-limit) | Google chặn tạm thời do spam OTP liên tục. | Đưa tài khoản vào danh sách `cooldown_7days`, đóng profile ngâm tĩnh 24h - 7 ngày để Google reset bộ đếm. |

---

## 4. Pitfall quan trọng khi phối hợp người dùng nhập OTP: GIỮ NGUYÊN PROFILE TRÊN MÀN HÌNH
- **Lỗi phổ biến của Agent**: Chạy script test xong tự động đóng browser (`page.close()`, `browser.close()`, `profiles/close`) trong khi người dùng đang chuẩn bị nhận mã OTP.
- **Quy tắc bắt buộc**:
  - Khi mở profile để cứu tài khoản hoặc chuẩn bị nhận mã OTP: Đặt tên profile rõ ràng (ví dụ: `CUU_ACC_<slot>_<email>`).
  - Sau khi đưa browser tới màn hình chờ OTP, ngắt kết nối CDP (`b.close()` trên CDP connection chỉ đóng client kết nối, hoặc để script chờ) nhưng **TUYỆT ĐỐI CẤM gọi API `profiles/close` hoặc `profiles/delete`**.
  - Báo cáo rõ ràng cho User: Profile nào đang mở sẵn trên màn hình, ở bước nào, để User thao tác nhập mã.

---

## 5. Quy trình chuẩn khi thuê số 5sim giải Checkpoint rồi gỡ số
Để tránh sau này bị kẹt lại vì mất số SIM ảo:
1. **Bước 1**: Thuê số 5sim (Việt Nam ~$0.18) -> Nhận OTP mở khóa đăng nhập.
2. **Bước 2**: Ngay khi vào được tài khoản, truy cập `myaccount.google.com/signinoptions/twosv` -> Bật **2FA TOTP (Google Authenticator)** và lưu Secret Key vào Excel.
3. **Bước 3**: Vào `myaccount.google.com/phone` hoặc `signinoptions/rescuephone` -> Xóa số điện thoại 5sim. Google chỉ hỏi mật khẩu hoặc mã TOTP vừa tạo -> Xóa thành công.
4. Từ đó tài khoản dùng 2FA TOTP vĩnh viễn, không phụ thuộc vào SIM.
