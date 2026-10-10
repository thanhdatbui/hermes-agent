# Hotmail Password Recovery, Sync & Reset Workflow (2026-10-10)

## 1. Password Mapping & Fallback Safety Invariant
- **CẤM TUYỆT ĐỐI fallback sang mật khẩu TikTok**: Khi đăng nhập Hotmail/Microsoft (`login.live.com`), chỉ được phép dùng trường `mail_password` (từ cột `PASS MAIL` trong Master Excel `taikhoan_dat_v2_updated .xlsx` hoặc cột 3 trong `gmail_clean_v2.xlsx`). Cấm tuyệt đối `info.get("mail_password") or info.get("password")` vì `password` là mật khẩu TikTok, đem điền vào Microsoft sẽ làm hòm thư bị flag/khóa.
- **Tự động đồng bộ `mail_password` vào State JSON**: Trong hàm `load_state` của supervisor, luôn đồng bộ trực tiếp `mail_password` từ Excel vào state nếu state chưa có hoặc Excel có giá trị mới. Không được loại trừ `mail_password` khi reconcile profile.

## 2. IMAP OTP Extraction từ Email Khôi Phục (`thanhdatbui1995@gmail.com`)
- **Credentials**: Lưu trong Windows Registry `HKCU\Environment`: `OTP_MAIL_USER` và `OTP_MAIL_APP_PASSWORD`.
- **Kết nối IMAP**: `imap.gmail.com:993` SSL.
- **Lấy OTP 6 số**:
  - Filter mail từ `"Microsoft"` hoặc Subject chứa `Đặt lại mật khẩu` / `Your single-use code`.
  - Bỏ qua mã link cố định của Microsoft `521839`.
  - Luôn kiểm tra timestamp tin nhắn (`Date` header) để đảm bảo OTP mới phát sinh sau thời điểm bấm "Gửi mã" (`not_before_ts`).

## 3. Quy trình Đặt Lại Mật Khẩu Mới (`account.live.com/password/reset`)
- **Phân biệt 2 luồng xác thực Microsoft**:
  - **Luồng A (Login Challenge trên `login.live.com`)**: Yêu cầu điền **FULL email** (`thanhdatbui1995@gmail.com`) vào ô `#proof-confirmation-email-input`, mã OTP 6 số điền vào 6 ô `#codeEntry-0` đến `#codeEntry-5`. *Lưu ý: Luồng này chỉ xác thực để vào phiên làm việc tạm thời, CHƯA thực hiện đổi mật khẩu.*
  - **Luồng B (Reset Password chính thức trên `account.live.com/password/reset`)**:
    1. Điều hướng thẳng tới `https://account.live.com/password/reset`.
    2. Điền email mục tiêu (`#iNext`).
    3. Chọn radio email khôi phục (`#textproofOption0`).
    4. Điền phần ẩn vào `#proofInput0`: **Chỉ điền phần username** (`thanhdatbui1995`), KHÔNG điền đuôi `@gmail.com` vì form đã có sẵn label `@gmail.com` bên cạnh ô input.
    5. Bấm `#iSelectProofAction` ("Nhận mã").
    6. Lấy OTP từ Gmail IMAP và điền vào ô `#iVerifyText` -> Bấm `#iVerifyIdentityAction`.
    7. Form đặt mật khẩu mới xuất hiện (`#Password` và `#RetypePassword`):
       - Chụp ảnh Pre-submit (Gate 6).
       - Điền mật khẩu mới đạt tiêu chuẩn bảo mật (chữ hoa, chữ thường, số, ký tự đặc biệt).
       - Bấm `#iResetPwdAction`.
       - Chụp ảnh Post-submit xác nhận tiêu đề xanh *"Thông tin bảo mật được cập nhật - Mật khẩu của bạn đã thay đổi"*.
- **Xử lý Rate Limit gửi OTP Microsoft**:
  - Nếu gửi OTP liên tiếp $\ge 3$ lần trong thời gian ngắn, Microsoft sẽ báo lỗi *"Bạn đã đạt đến giới hạn của mình với phương thức đăng nhập này"*.
  - Biện pháp: Lập tức dừng thao tác, set cooldown tối thiểu **2 tiếng** trong state cho profile đó để tránh bị khóa vĩnh viễn phương thức khôi phục.
- **Đồng bộ 3 điểm bắt buộc sau khi đổi mật khẩu**:
  - Master Excel `taikhoan_dat_v2_updated .xlsx` (cột `PASS MAIL` / cột 7).
  - `gmail_clean_v2.xlsx` (cột 3).
  - State JSON (`batch_gpm_5profiles_supervisor_state.json`).

## 4. Đối Soát Nguồn Gốc Mua Mail & Phân Loại Tài Khoản Sai Pass
- **Dấu hiệu nhận biết tài khoản đã gắn mail khôi phục vs chưa gắn**:
  - Khi bấm *"Bạn quên mật khẩu?"*:
    - **ĐÃ GẮN**: Microsoft hiện rõ tùy chọn gửi mã về `th*****@gmail.com`. Có thể cứu tự động qua luồng OTP IMAP.
    - **CHƯA GẮN**: Microsoft nhảy thẳng sang form nộp đơn thủ công (`account.live.com/acsr` - *"Khôi phục tài khoản của bạn - Nhập vào địa chỉ email khác để chúng tôi liên hệ"*). KHÔNG thể khôi phục tự động qua OTP.
- **Nguồn gốc tài khoản Hotmail Loại 2 (Graph API)**:
  - Các tài khoản được mua tự động qua API BoxTaiKhoan (`boxtaikhoan.com`, user `thanhdatbui1995`, Product ID 60/129) ban đầu được lưu mật khẩu gốc từ shop vào cột `PASS MAIL`.
  - Luồng reg TikTok trên Android chỉ sử dụng Microsoft Graph API Token để đọc OTP ngầm, hoàn toàn không đăng nhập bằng mật khẩu web.
  - Khi tài khoản chưa được chạy luồng Change Security/Add Recovery Mail, mật khẩu gốc của shop có thể bị vô hiệu hoặc đổi sau thời gian dài, dẫn đến việc login web thất bại.

## 5. Giao tiếp với User
- Dùng từ ngữ đơn giản, trực diện: nói "tên nick TikTok" hoặc "tài khoản TikTok", tuyệt đối không dùng biệt ngữ kỹ thuật thừa thãi như "TikTok ID handle".
