# Hotmail Password Mapping & Cookie Consent Pitfalls (2026-10-10)

## 1. Bẫy Suy Diễn Sai "Shop Bán Sai Pass / Nick Đã Bị Đổi Pass"
- **Hiện tượng:** Tài khoản Hotmail đã reg thành công TikTok (nhận OTP ngon lành trên thiết bị), nhưng khi supervisor tự động đăng nhập Hotmail trên GPMLogin để reg ChatGPT hoặc nạp pool thì Microsoft báo đỏ: *"Mật khẩu đó không đúng với tài khoản Microsoft của bạn"*.
- **Sai lầm tai hại của Agent:** Vội vàng kết luận "shop bán sai pass", "nick đã từng bị đổi pass", hoặc "hết hạn bảo hành 24h" mà không kiểm tra dữ liệu nội bộ.
- **Root Cause cốt lõi trong code:**
  1. Trong `batch_gpm_5profiles_supervisor.py` hàm `load_state`, khi profile đã có sẵn trong state JSON, lệnh update loại trừ các trường password:
     ```python
     profiles[key].update({k: v for k, v in account.items() if k not in {"password", "mail_password", "chatgpt_password"}})
     ```
     Dẫn đến việc nếu ban đầu `mail_password` bị rỗng (hoặc nạp thiếu), state sẽ vĩnh viễn không bao giờ được cập nhật lại từ Excel.
  2. Tại hàm `execute`, lệnh chạy script login Hotmail có fallback tai hại:
     ```python
     "--password", info.get("mail_password") or info.get("password") or ""
     ```
     Trong hệ thống Taadaa, trường `password` là cột `PASS` (mật khẩu TikTok của nick), còn mật khẩu Hotmail nằm ở cột `PASS MAIL`. Khi `mail_password` rỗng, script tự động lấy mật khẩu TikTok đem đăng nhập vào Microsoft Live.
  3. **Kết quả:** Microsoft báo sai pass 100%, nick bị đày vào Cooldown 48h oan uổng dù mật khẩu trong Excel vẫn đúng.
- **Quy tắc phòng ngừa bất biến:**
  - Luôn đồng bộ `mail_password` từ cột `PASS MAIL` vào state nếu Excel có dữ liệu.
  - CẤM TUYỆT ĐỐI fallback sang trường `password` TikTok khi đăng nhập Hotmail. Nếu thiếu `mail_password` phải fail-closed báo thiếu dữ liệu để kiểm tra Excel, không được lấy pass của dịch vụ khác gõ bừa vào Microsoft.

## 2. Bằng Chứng Nhận Biết Tài Khoản ĐÃ TỪNG ĐỔI PASS (Change Info)
- Mail mua từ shop (`boxtaikhoan.com`, `clonefbig.com`...) ban đầu chỉ có mail khôi phục mặc định dạng `...fviainboxes.com` hoặc không có mail khôi phục.
- Khi truy cập màn hình đăng nhập hoặc quên mật khẩu, nếu Microsoft hiển thị gợi ý:
  `"Gửi mã đến th*****@gmail.com"` (hoặc email khôi phục cá nhân của Operator)
  -> **Điều này chứng minh 100% tài khoản này đã từng được User/hệ thống thực hiện quy trình ĐỔI MẬT KHẨU / THÊM MAIL KHÔI PHỤC trước đây!**
- **Nguyên nhân mất mật khẩu mới (Lưu ẩu):**
  - Script đổi mật khẩu (`gpm_change_hotmail_security.py`) chỉ cập nhật vào `gmail_clean_v2.xlsx` mà bỏ quên Master Tracking `taikhoan_dat_v2_updated .xlsx`.
  - OneDrive/Excel lock tiến trình ghi file làm lệnh `wb.save()` thất bại âm thầm, làm mất chuỗi mật khẩu mới.
  - **Khắc phục:** Khi tài khoản đã có mail khôi phục cá nhân mà mất pass, bắt buộc dùng quy trình khôi phục: gửi OTP về Gmail cá nhân -> reset mật khẩu mới -> đồng bộ ngay lập tức vào CẢ HAI file Excel (`gmail_clean_v2.xlsx` Cột 3 và `taikhoan_dat_v2_updated .xlsx` Cột 7).

## 3. Bẫy Microsoft Cookie Consent Banner
- **Hiện tượng:** Sau khi submit mật khẩu Hotmail đúng, Microsoft chuyển hướng qua `auth/complete-client-signin-oauth-silent` và bật modal/banner Cookie Consent: *"Chúng tôi dùng cookie tùy chọn để cải thiện trải nghiệm của bạn... [Chấp nhận] [Từ chối]"*.
- Nếu script không click banner này, trang web bị dừng lại ở URL chuyển hướng hoặc landing ban đầu, khiến detector nhận nhầm là tài khoản bị kẹt/BLOCKED.
- **Xử lý chuẩn:**
  - Quét và click ngay các selector của cookie banner:
    ```python
    cookie_selectors = [
        "button:has-text('Accept')", "button:has-text('Chấp nhận')",
        "input[value='Accept']", "input[value='Chấp nhận']",
        "#acceptButton", "#onetrust-accept-btn-handler",
        "button[id*='accept']", "button[id*='Accept']",
        "button:has-text('Từ chối')", "button:has-text('Decline')",
    ]
    ```
  - Chờ trang hoàn tất chuyển tiếp sang `https://account.microsoft.com/account` rồi mới chụp ảnh Post-submit và xác nhận `LOGIN SUCCESS`.

## 4. Đồng Bộ `last_result` Khi Cứu Hộ Profile
- Báo cáo định kỳ (Lifecycle 6h) kiểm tra lỗi qua cả `info.get("status")` và `info.get("last_result", {}).get("status")`.
- Khi can thiệp cứu hộ một profile từ FAILED/BLOCKED sang PENDING/COMPLETED, bắt buộc phải làm sạch hoặc cập nhật `last_result` sang `COMPLETED`, tránh việc profile đã chạy xong nhưng báo cáo 6h vẫn đếm nhầm vào danh sách "CẦN XỬ LÝ".

## 5. Kỷ Luật Giao Tiếp & Thuật Ngữ
- **CẤM DÙNG THUẬT NGỮ JARGON GÂY KHÓ CHỊU:** Tuyệt đối không gọi tài khoản TikTok là `@handle` hay `TikTok ID handle`. Trong hệ thống và giao tiếp với User, chỉ gọi đơn giản là **ID** hoặc **tên nick TikTok** (ví dụ: `@thanhlee327`, nick `thanhlee327`).

## 6. Quy Trình Cứu Nick Tự Động Qua GPM Playwright + Gmail IMAP OTP (2026-10-10)
- **Phát hiện form có mail khôi phục cá nhân:**
  - Khi Microsoft hiển thị: *"Xác minh email của bạn - Chúng tôi sẽ gửi mã đến th*****@gmail.com"* -> Điền email khôi phục đầy đủ (`thanhdatbui1995@gmail.com`) vào selector `#proof-confirmation-email-input` -> Click `button:has-text('Gửi mã')`.
  - Phân biệt với form không có mail khôi phục: Nếu là form *"Khôi phục tài khoản của bạn - Nhập địa chỉ email khác để liên hệ..."* -> Tài khoản chưa gán mail khôi phục cá nhân, không thể cứu bằng luồng OTP tự động.
- **Lấy OTP 6 số từ Gmail qua IMAP:**
  - Đọc credentials từ Windows Environment (`winreg.HKEY_CURRENT_USER\Environment`):
    - `OTP_MAIL_USER`: `thanhdatbui1995@gmail.com`
    - `OTP_MAIL_APP_PASSWORD`: App password (16 ký tự).
  - Kết nối `imap.gmail.com:993`, tìm email mới nhất từ `Microsoft` / `account-security-noreply@accountprotection.microsoft.com`.
  - **BẪY CẦN TRÁNH:** Bỏ qua mã `521839` (đây là ID link chính sách quyền riêng tư của Microsoft nằm trong email, không phải OTP).
- **Điền OTP 6 số trên giao diện web:**
  - Microsoft phân chia thành 6 ô input riêng biệt: `#codeEntry-0` đến `#codeEntry-5`.
  - Lặp qua 6 chữ số và điền vào từng ô tương ứng (delay 0.1s mỗi ô).
- **Xử lý các màn hình chuyển tiếp sau khi nhập OTP:**
  - **Điều khoản (Terms):** Click *"Tiếp theo"* (`button:has-text('Tiếp theo'), #iNext`).
  - **Duy trì đăng nhập (KMSI):** Click *"Không"* (`#idBtn_Back`, `input[value='Không']`) -> Microsoft sẽ hoàn tất auth và chuyển hướng ngay lập tức vào Dashboard, tránh bị kẹt sticky prompt nếu click "Có".
  - **Cookie Consent:** Click *"Chấp nhận"* (`button:has-text('Chấp nhận')`).
- **Xử lý Rate Limit khi thử lại:**
  - Nếu gửi OTP liên tiếp > 3 lần trong thời gian ngắn, Microsoft sẽ chặn tạm thời: *"Bạn đã đạt đến giới hạn của mình với phương thức đăng nhập này"*.
  - Biện pháp: Set cooldown tối thiểu 2 giờ trong file state json để Microsoft hạ nhiệt trước khi thực hiện lại.
