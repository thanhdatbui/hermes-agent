# Hotmail Change Info: Recovery Email & 2FA Flow (2026-10-12)

## 1. Kết quả kiểm chứng thực tế live (2026-10-13): Microsoft BẮT BUỘC có Mail khôi phục mới cho bật 2FA
- **Sự thật kỹ thuật được kiểm chứng qua Canary:**
  - Trên nick Zin trắng chỉ có mật khẩu (`AlyceBroberg15774@hotmail.com`):
    * Khi click `#Add_msAuthApp` trong modal proofs: Microsoft từ chối mở form cài đặt và tự động đóng modal.
    * Khi truy cập thẳng `https://account.live.com/proofs/EnableTfa`: Microsoft chặn đứng và hiển thị thông báo bắt buộc: *"Để bật xác nhận hai bước, chúng tôi cần hai cách để chắc chắn bạn là bạn. Bạn có muốn nhận mã xác nhận thứ hai của mình không?"* kèm form ép nhập email/SĐT khôi phục.
  - Trên nick đã add email khôi phục (`MarilynnCott83008@hotmail.com`): Microsoft lập tức cho phép mở form Authenticator App, trích xuất 2FA Secret Key TOTP và bật 2FA thành công 100%.
- **Quy tắc bất biến:** Tài khoản Hotmail Zin BẮT BUỘC phải add Mail khôi phục trước (dùng domain tạm `@fviainboxes.com`) ➔ Xác minh OTP ➔ Sau đó mới Add 2FA Authenticator TOTP.
- **Về việc ngâm:** HOÀN TOÀN KHÔNG CẦN NGÂM THÊM sau khi add mail khôi phục! Vừa add mail khôi phục xong là add được 2FA Authenticator ngay trong cùng 1 phiên.

## 2. Thứ tự thực thi chuẩn liên hoàn (5 Bước Khép Kín)
Không cần ngâm thêm. Thực hiện tuần tự trong cùng 1 phiên:
1. **Bước 1: Add Mail Khôi Phục (Domain tạm `@fviainboxes.com`):**
   - Kiểm tra xem trên trang proofs đã có mail khôi phục chưa (thẻ "Gửi mã qua email"). Nếu đã có sẵn -> Bỏ qua bước này.
   - Nếu chưa có: Mở modal -> Chọn "Gửi mã qua email" (`#Add_email`) -> Điền mail `<username><3_rand>@fviainboxes.com` -> Bóc OTP qua API `fviainboxes.com/messages` -> Điền xác minh.
2. **Bước 2: Thiết lập 2FA Authenticator (TOTP) & Bật công tắc tổng:**
   - Mở modal -> Chọn "Sử dụng ứng dụng" (`#Add_msAuthApp`) -> Chọn "Tôi muốn sử dụng ứng dụng xác thực khác" (`#iSelectProofTypeAlternate`).
   - Bấm tiếp theo -> Chọn hiển thị secret key dạng text (`#iShowPlainLink`).
   - Bóc Secret Key (16 ký tự Base32) -> Lưu vào Cột 4 của `gmail_clean_v2.xlsx`.
   - Sinh mã TOTP 6 số bằng `pyotp` -> Điền vào `#iTOTPField` và xác nhận.
   - Điều hướng tới `https://account.live.com/proofs/EnableTfa` để bật công tắc Two-step verification tổng.
3. **Bước 3: Đổi mật khẩu mới:**
   - Điều hướng `https://account.live.com/password/change` -> Nhập mật khẩu hiện tại -> Điền mật khẩu mới (chuỗi 14 ký tự ngẫu nhiên) -> Submit. Lưu Cột 3 Excel.
4. **Bước 4: Đăng xuất khỏi mọi nơi (Sign out everywhere):**
   - Quay lại trang `proofs` -> Click `#DeleteTrustedDevices` -> Xác nhận dialog "Đăng xuất" để hủy mọi phiên cũ toàn cầu.
5. **Bước 5: Đăng nhập lại (Relogin & KMSI):**
   - Điều hướng `https://login.live.com` -> Điền email + mật khẩu mới.
   - Nếu Microsoft đòi mã 2FA -> Dùng Secret Key vừa lưu sinh mã TOTP điền vào.
   - Bấm "Có" tại màn hình Duy trì đăng nhập (KMSI) để lưu phiên sống bền vững trên profile GPM.

## 3. Pitfall: Bấm nhầm nút Tiếp theo của Form
- Trong hàm `handle_microsoft_interstitials` (xử lý màn hình điều khoản/KMSI): BẮT BUỘC bỏ qua kiểm tra nút "Tiếp theo" khi URL đang chứa `proofs` (`if "proofs" in page.url.lower(): pass`).
- Nếu không kiểm tra URL, bot sẽ tưởng nút "Tiếp theo" của form proofs là màn hình điều khoản và click trước khi điền dữ liệu, gây lỗi submit rỗng.

## 4. Đóng tab Chrome CDP
- Đóng tab qua CDP endpoint `/json/close/{target_id}` chỉ giải phóng RAM render, hoàn toàn không mất cookies hay session đăng nhập do toàn bộ session được Chrome lưu bền vững trên ổ đĩa Profile.
