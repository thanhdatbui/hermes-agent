# Hotmail Change Info: Recovery Email & 2FA Flow (2026-10-12)

## 1. Kết quả kiểm chứng thực tế live (2026-10-13): Microsoft BẮT BUỘC có Mail khôi phục mới cho bật 2FA
- **Sự thật kỹ thuật được kiểm chứng qua Canary:**
  - Trên nick Zin trắng chỉ có mật khẩu (`AlyceBroberg15774@hotmail.com`):
    * Khi click `#Add_msAuthApp` trong modal proofs: Microsoft từ chối mở form cài đặt và tự động đóng modal.
    * Khi truy cập thẳng `https://account.live.com/proofs/EnableTfa`: Microsoft chặn đứng và hiển thị thông báo bắt buộc: *"Để bật xác nhận hai bước, chúng tôi cần hai cách để chắc chắn bạn là bạn. Bạn có muốn nhận mã xác nhận thứ hai của mình không?"* kèm form ép nhập email/SĐT khôi phục.
  - Trên nick đã add email khôi phục (`MarilynnCott83008@hotmail.com`): Microsoft lập tức cho phép mở form Authenticator App, trích xuất 2FA Secret Key TOTP và bật 2FA thành công 100%.
- **Quy tắc bất biến:** Tài khoản Hotmail Zin BẮT BUỘC phải add Mail khôi phục trước (dùng domain tạm `@fviainboxes.com`) ➔ Xác minh OTP ➔ Sau đó mới Add 2FA Authenticator TOTP.
- **Về việc ngâm:** HOÀN TOÀN KHÔNG CẦN NGÂM THÊM sau khi add mail khôi phục! Vừa add mail khôi phục xong là add được 2FA Authenticator ngay trong cùng 1 phiên.

## 2. Thứ tự thực thi chuẩn liên hoàn (5 Bước Khép Kín) & Nguyên Tắc Ghi Dữ Liệu Lũy Tiến
- **Nguyên tắc ghi dữ liệu lũy tiến (Write-Through Persistence — Chống mất dữ liệu):**
  * TUYỆT ĐỐI KHÔNG đợi đến khi hết phiên hay đợi đăng nhập lại (relogin) mới ghi file Excel.
  * Làm tới bước nào, thành công bước nào là BẮT BUỘC ghi ngay lập tức xuống ổ cứng bước đó. Nếu rớt mạng hay crash ở bước sau thì tài khoản vẫn bảo toàn 100% dữ liệu mới.

Thực hiện tuần tự trong cùng 1 phiên:
1. **Bước 1: Add Mail Khôi Phục (Domain tạm `@fviainboxes.com`):**
   - Kiểm tra xem trên trang proofs đã có mail khôi phục chưa (thẻ "Gửi mã qua email"). Nếu đã có sẵn -> Bỏ qua bước này.
   - Nếu chưa có: Mở modal -> Chọn "Gửi mã qua email" (`#Add_email`) -> Điền mail `<username><3_rand>@fviainboxes.com` -> Bóc OTP qua API `fviainboxes.com/messages` -> Điền xác minh.
   - **GHI NGAY VÀO EXCEL:** Ngay khi Microsoft xác nhận OTP hợp lệ -> Ghi ngay địa chỉ mail khôi phục vào Cột 5 `gmail_clean_v2.xlsx`.
2. **Bước 2: Thiết lập 2FA Authenticator (TOTP) & Bật công tắc tổng:**
   - Mở modal -> Chọn "Sử dụng ứng dụng" (`#Add_msAuthApp`) -> Chọn "Tôi muốn sử dụng ứng dụng xác thực khác" (`#iSelectProofTypeAlternate`).
   - Bấm tiếp theo -> Chọn hiển thị secret key dạng text (`#iShowPlainLink`).
   - Bóc Secret Key (16 ký tự Base32) -> **GHI NGAY VÀO CỘT 4 `gmail_clean_v2.xlsx`** trước khi kích hoạt.
   - Sinh mã TOTP 6 số bằng `pyotp` -> Điền vào `#iTOTPField` và xác nhận.
   - Điều hướng tới `https://account.live.com/proofs/EnableTfa` để bật công tắc Two-step verification tổng.
3. **Bước 3: Đổi mật khẩu mới:**
   - Điều hướng `https://account.live.com/password/change` -> Nhập mật khẩu hiện tại -> Điền mật khẩu mới (chuỗi 14 ký tự ngẫu nhiên) -> Submit.
   - **GHI NGAY VÀO CẢ 2 FILE EXCEL TRƯỚC KHI SIGN OUT:** Khi Microsoft chấp nhận đổi mật khẩu (không lỗi), ghi ngay lập tức vào:
     * Cột 3 của `gmail_clean_v2.xlsx` (Đồng thời xóa token OAuth cũ Cột 9 vì đã bị revoke).
     * Cột G (Cột 7 - PASS MAIL) workbook farm `taikhoan_dat_v2_updated .xlsx`.
     * Ghi nhận vào state tracker `STATE_FILE`.
4. **Bước 4: Đăng xuất khỏi mọi nơi (Sign out everywhere):**
   - Quay lại trang `proofs` -> Click `#DeleteTrustedDevices` -> Xác nhận dialog "Đăng xuất" để hủy mọi phiên cũ toàn cầu.
5. **Bước 5: Đăng nhập lại (Relogin & KMSI):**
   - Điều hướng `https://login.live.com` -> Điền email + mật khẩu mới.
   - Nếu Microsoft đòi mã 2FA -> Dùng Secret Key vừa lưu sinh mã TOTP điền vào.
   - Bấm "Có" tại màn hình Duy trì đăng nhập (KMSI) để lưu phiên sống bền vững trên profile GPM.
   - Hoàn tất chuyển stage sang `DONE`.

## 3. Pitfalls & Tránh Lỗi Thao Tác UI GPM/CDP
- **Nhầm lẫn ô input `ai_do@example.com` khi bật 2FA:**
  * Màn hình `https://account.live.com/proofs/EnableTfa` của Microsoft bản địa hóa tiếng Việt hiển thị placeholder `ai_do@example.com` (tương đương `someone@example.com`).
  * Đây KHÔNG PHẢI lỗi hay giao diện nhập code 2FA, mà là bằng chứng Microsoft đang chặn luồng và ép nhập email khôi phục thứ hai trước khi mở luồng 2FA.
- **Bấm nhầm nút Tiếp theo của Form:**
  * Trong hàm `handle_microsoft_interstitials` (xử lý màn hình điều khoản/KMSI): BẮT BUỘC bỏ qua kiểm tra nút "Tiếp theo" khi URL đang chứa `proofs` (`if "proofs" in page.url.lower(): pass`).
  * Nếu không kiểm tra URL, bot sẽ tưởng nút "Tiếp theo" của form proofs là màn hình điều khoản và click trước khi điền dữ liệu, gây lỗi submit rỗng.
- **Selector chính xác trong Modal Proofs Microsoft:**
  * Option "Sử dụng ứng dụng": selector là `#Add_msAuthApp` (thẻ `<a>` có class `.box.passkey`), không phải button đơn thuần.
  * Option "Gửi mã qua email": selector là `#Add_email`.
- **Đồng bộ STAGE_ORDER trong Supervisor (`batch_gpm_5profiles_supervisor.py`):**
  * Đóng gói stage `CHANGE_INFO` thành luồng độc lập, khi hoàn thành chuyển thẳng sang `DONE`.
  * STAGE_ORDER chuẩn: `["HOTMAIL_LOGIN", "CHATGPT_REG", "CODEX_OAUTH", "WAIT_7D", "CHANGE_INFO", "DONE"]`. Không chia vụn thành các sub-stage riêng biệt gây kẹt supervisor.

## 4. Đóng tab Chrome CDP
- Đóng tab qua CDP endpoint `/json/close/{target_id}` chỉ giải phóng RAM render, hoàn toàn không mất cookies hay session đăng nhập do toàn bộ session được Chrome lưu bền vững trên ổ đĩa Profile.
