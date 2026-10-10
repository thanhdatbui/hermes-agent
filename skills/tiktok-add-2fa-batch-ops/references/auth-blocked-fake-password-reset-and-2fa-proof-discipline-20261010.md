# Xử Lý Mật Khẩu Sai (AUTH_BLOCKED), Phục Hồi Pass Excel & Kỷ Luật Nghiệm Thu 2FA (10/10/2026)

## 1. Bản chất sự cố Mật khẩu sai / Pass láo trong Excel gây treo `AUTH_BLOCKED`
- **Hiện tượng**:
  * Khi chạy `tiktok_login_v1.py` hoặc `run_capture_phase_b.py` cho tài khoản có sẵn mật khẩu trong cột Password của file Excel (`taikhoan_dat_v2_updated .xlsx`), script điền mật khẩu vào form TikTok.
  * TikTok báo "Mật khẩu sai", nhưng trường mật khẩu vẫn còn dấu chấm `•••••••••••••`.
  * Cơ chế bảo vệ fail-closed của runner phát hiện form password không chuyển tiếp và kích hoạt:
    `[AUTH_BLOCKED] 🛑 Mật khẩu đã được điền nhưng TikTok vẫn ở màn hình password (nghi vấn sai pass hoặc form error)! CẤM ĐIỀN LẠI LẦN 2! DỪNG NGAY!`
  * Script dừng ngay lập tức (exit code 2) để chống bị khóa tài khoản hoặc dính checkpoint.
- **Hậu quả**:
  * Các tài khoản dính mật khẩu sai trong Excel (ví dụ: `@ngohuong0265` trên M261, `@annapmfdh0a` trên M44, `@mgpovhrgnnq` trên M53) sẽ bị kẹt vĩnh viễn ở khâu login/2FA nếu không can thiệp.
- **Quy trình giải cứu chuẩn hóa (Recovery Protocol)**:
  1. **Xóa mật khẩu sai trong Excel về `None`**:
     * Mở workbook (cả file Kibe và Admin nếu cần), tìm đúng dòng của tài khoản và set `ws.cell(row=R, column=4).value = None`.
  2. **Đăng nhập cứu hộ qua OTP (Bypass Password)**:
     * Chạy `tiktok_login_v1.py <STT> --email <user/email> --ss --no-track --otp-only`.
     * Script sẽ bỏ qua bước nhập pass sai, yêu cầu TikTok gửi mã OTP về hòm thư Hotmail/Outlook, tự đọc OTP qua Microsoft Graph API (PC) và đăng nhập thành công vào app.
  3. **Đổi mật khẩu mới & Bật 2FA**:
     * Trong `run_capture_phase_b.py`, hàm `password_needs_rotation(None)` trả về `True` khi pass là `None`.
     * Khi chạy Phase B, adapter sẽ nhận diện tài khoản chưa có pass và kích hoạt luồng đổi mật khẩu mới an toàn, sau đó ghi pass mới 18 ký tự vào cột Password và khóa 2FA Secret vào cột 2FA của workbook.

---

## 2. Vá lỗi nút điều hướng song ngữ (`UI_TARGET_AMBIGUOUS:Next:0`)
- **Nguyên nhân**:
  * Trên các máy Samsung S7 (Android 7/8), ngôn ngữ hiển thị của TikTok có thể là tiếng Việt (`"Tiếp tục"`, `"Tiếp"`, `"Gửi mã"`) hoặc tiếng Anh (`"Next"`, `"Continue"`, `"Send code"`).
  * Trong `live_phase_b_adapter.py`, các hàm như `advance_to_otp()` và `ensure_account_password_saved()` ban đầu chỉ tìm nhãn cứng dẫn đến lỗi `UI_TARGET_AMBIGUOUS:Next:0` khi không thấy nút tiếng Anh.
- **Giải pháp**:
  * Quét danh sách nhãn song ngữ: `["Tiếp tục", "Tiếp", "Gửi mã", "Next", "Send code", "Continue"]` với cả `prefix=False` và `prefix=True`.
  * Khi có nhiều node khớp hoặc node con lồng trong button, fallback chọn phần tử có tọa độ Y lớn nhất (`max(matches, key=lambda el: el.center[1])` - nút nằm dưới cùng màn hình).

---

## 3. Kỷ luật tách bạch giữa Trạng thái 2FA và Trạng thái Mật khẩu
- **CẤM TUYỆT ĐỐI** báo cáo gộp: *"Đã bật 2FA và đổi mật khẩu mới thành công"* khi ô Password trong Excel vẫn đang là `None`!
- **Thực tế kỹ thuật**:
  * Trong Phase B, việc ghi nhận 2FA Authenticator thành công (đã có 2FA Secret) có thể hoàn tất độc lập trước bước đổi mật khẩu. Nếu bước đổi pass gặp lỗi điều hướng hoặc fail-safe thoát ra để bảo toàn secret trong journal, mật khẩu TikTok vẫn chưa đổi và ô Excel vẫn là `None`.
- **Quy tắc báo cáo bắt buộc**:
  * Phải tách bạch thành checklist rõ ràng:
    - **2FA Secret**: `[ĐÃ BẬT - Mã Secret 32 ký tự]`
    - **Mật khẩu mới**: `[CHƯA ĐỔI / ĐANG LÀ NONE]` (hoặc `[ĐÃ ĐỔI - Mật khẩu mới]`)
  * Báo cáo trung thực trạng thái từng trường ngay dòng đầu tiên, không mập mờ để User phải tự gặng hỏi.

---

## 4. Kỷ luật thị giác: Nghiệm thu 2FA bắt buộc chụp đúng màn hình Bảo Mật
- **CẤM TUYỆT ĐỐI**: Chụp ảnh Account Switcher hoặc Profile rồi gửi làm bằng chứng 2FA!
  * Ảnh Switcher/Profile chỉ chứng minh nick đã đăng nhập, KHÔNG chứng minh 2FA đang bật.
- **BẮT BUỘC**:
  * Điều hướng vào: *Hồ sơ > Menu 3 gạch > Cài đặt và quyền riêng tư > Bảo mật > Xác minh 2 bước*.
  * Chụp ảnh màn hình hiển thị rõ:
    1. Tiêu đề: **"Xác minh 2 bước đang bật"**.
    2. Phương thức: **"Trình xác thực: Bật"**.
    3. Phương thức: **"Mật khẩu: Bật"** (nếu có).
  * Chạy WinRT OCR / Vision soi mắt kiểm tra đúng các token trên trước khi gửi thẻ `MEDIA:<path>`.
