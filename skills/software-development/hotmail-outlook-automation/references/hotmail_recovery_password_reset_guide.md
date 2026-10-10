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

## 4. Đối Soát Nguồn Gốc Mua Mail & Chẩn Đoán Gốc Rễ Lỗi Sai Mật Khẩu
- **Nguyên lý bất biến (Sàn không bao giờ tự đổi pass)**: Các bên sàn/shop bán tài khoản (như BoxTaiKhoan, CloneFBIG) không bao giờ tự ý đổi mật khẩu của tài khoản đã bán cho khách. Khi tài khoản mua về bị báo sai mật khẩu trên web Microsoft, nguyên nhân BẮT BUỘC thuộc về 1 trong 2 trường hợp sau:
  1. **Trường hợp 1 — Đã chạy đổi pass trên Microsoft mà KHÔNG LƯU xuống Excel (Out-of-order execution bug)**:
     - Trong các script đổi thông tin/đổi pass (`gpm_change_hotmail_security.py`), bước gửi submit đổi mật khẩu lên server Microsoft (`#UpdatePasswordAction`) nằm trước bước chụp ảnh và đăng nhập lại.
     - Nếu Microsoft đã đổi pass thành công nhưng sau đó gặp timeout, crash trình duyệt, hoặc ngắt kết nối CDP ở bước chụp ảnh/relogin, script nhảy thẳng vào `except Exception` $\rightarrow$ **bước ghi vào Excel (`PASS MAIL`) và State JSON bị bỏ qua hoàn toàn**.
     - Mật khẩu mới được sinh ngẫu nhiên trong RAM bị mất khi tiến trình kết thúc, còn Excel vẫn lưu mật khẩu cũ từ thời mới mua.
     - **Biện pháp kiến trúc bắt buộc**: BẮT BUỘC ghi đè mật khẩu mới vào Master Excel và State JSON NGAY LẬP TỨC (Immediate Flush) ngay khi click submit đổi pass thành công, TRƯỚC KHI thực hiện bất kỳ thao tác phụ nào khác (screenshot, relogin).
  2. **Trường hợp 2 — Mật khẩu Web bị lưu sai / chưa từng được kiểm chứng từ đầu**:
     - Với dòng Hotmail Graph API (Loại 2), luồng reg TikTok trên điện thoại chỉ dùng `refresh_token` để gọi Microsoft Graph API đọc OTP ngầm, hoàn toàn không đăng nhập bằng mật khẩu trên web `login.live.com`.
     - Nếu chuỗi password trả về từ API sàn lúc mua bị lỗi format/sai ký tự, hoặc tài khoản thuộc diện đã qua dịch vụ khác (như Product ID 57 / 22874) mà mật khẩu web không khớp, mật khẩu sai vẫn nằm trong Excel và chỉ bị lộ ra khi đưa vào pipeline login GPM Web sau này.
- **Dấu hiệu nhận biết tài khoản đã gắn mail khôi phục vs chưa gắn**:
  - Khi bấm *"Bạn quên mật khẩu?"*:
    - **ĐÃ GẮN (`th*****@gmail.com`)**: Microsoft hiện rõ tùy chọn gửi mã về `th*****@gmail.com` $\rightarrow$ Đã từng được user/hệ thống đổi thông tin bảo mật. BẮT BUỘC khôi phục qua luồng OTP IMAP Gmail và đặt lại mật khẩu mới tinh.
    - **CHƯA GẮN**: Microsoft nhảy thẳng sang form nộp đơn thủ công (`account.live.com/acsr` - *"Khôi phục tài khoản của bạn - Nhập vào địa chỉ email khác để chúng tôi liên hệ"*). KHÔNG thể khôi phục tự động qua OTP.

## 5. Quy Định Giao Tiếp Với User
- **CẤM TUYỆT ĐỐI dùng biệt ngữ kỹ thuật rườm rà**: CẤM dùng từ `"TikTok ID handle"`, `"handle"`, `"identifier"`. Luôn luôn gọi bằng từ ngữ thuần Việt tự nhiên: **`"tên nick TikTok"`** hoặc **`"tên nick"`**.
- **Giải trình sự cố trung thực & có căn cứ kỹ thuật**: Không bao giờ đổ lỗi vô căn cứ cho bên thứ ba (như suy diễn shop tự đổi pass) khi chưa kiểm tra kỹ toàn bộ logic lưu dữ liệu và log thực thi của hệ thống.
