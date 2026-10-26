# ChatGPT Web Pool Feeding & GPM Account Lifecycle Rules

## 1. Bản chất nhận diện tài khoản Đã Reg vs Chưa Reg ChatGPT
- **Dấu hiệu `/about-you` ("Bạn bao nhiêu tuổi?" / "How old are you?"):**
  - Khi điền email vào form login của ChatGPT Web, nếu hệ thống điều hướng sang `auth.openai.com/about-you` đòi điền Họ tên và Tuổi, đây là **BẰNG CHỨNG 100% TÀI KHOẢN ĐÓ CHƯA HỀ ĐƯỢC ĐĂNG KÝ TRƯỚC ĐÂY** (đây là New User Onboarding, KHÔNG PHẢI re-login challenge).
  - TUYỆT ĐỐI KHÔNG ngộ nhận màn hình này là bước xác thực lại của tài khoản cũ.
- **Tài khoản đã đăng ký thật sự:**
  - Nếu session cookie còn sống: mở `https://chatgpt.com/` là vào thẳng giao diện chat, cookie `__Secure-next-auth.session-token` có sẵn trong browser context.
  - Nếu session cookie hết hạn: sau khi nhập email, OpenAI chuyển sang `auth.openai.com/email-verification` để đòi OTP 6 số. Sau khi nhập đúng OTP sẽ vào thẳng chat hoặc hỏi mật khẩu cũ, không nhảy sang tạo tài khoản mới nếu thông tin cá nhân đã có.
- **Rà soát kho trước khi nạp pool:**
  - CẤM TUYỆT ĐỐI chỉ quét tên profile `@hotmail.com` trong SQLite GPMLogin để lấy candidate nạp pool (sẽ bốc nhầm các acc mới chỉ dừng ở bước tạo profile `HOTMAIL_LOGIN`).
  - BẮT BUỘC đối soát chéo với file supervisor state (`stage in ("DONE", "WAIT_7D", "CHANGE_INFO")` và `chatgpt_registered_at` có timestamp hợp lệ) hoặc kiểm tra log direct registration (`chatgpt_gpm_direct_reg.log`).

## 2. Quy chuẩn GPMLogin Database & API
- **Bẫy Profile trong Thùng Rác (`GroupId == 0` / `PROFILE_IN_TRASH`):**
  - Trong bảng `Profiles` của `profile_data.db` (GPMLogin), các profile nằm trong thùng rác có `GroupId = 0`.
  - Gọi API `/profiles/start/{id}` với các profile này sẽ trả về lỗi `PROFILE_IN_TRASH` và gây loop retry làm nghẽn tiến trình.
  - BẮT BUỘC lọc điều kiện: `WHERE GroupId != 0`.
- **Khởi động GPM không gây chiếm RAM/CPU:**
  - Chạy theo luồng worker kiểm soát chặt (tối đa 3-5 workers song song).
  - Ngay sau khi trích xuất xong session token hoặc phát hiện session expired, BẮT BUỘC đóng dứt điểm profile GPM (`/profiles/stop/{id}`) và kill tiến trình `chrome.exe` mồ côi tương ứng theo profile ID để giải phóng RAM ngay lập tức.

## 3. Quy trình bóc tách OTP tự động qua Microsoft Graph API
- **Nguồn xác thực:**
  - Đọc `refresh_token` và `client_id` từ `admin/gmail_clean_v2.xlsx` hoặc `kibe/gmail_clean_v2.xlsx`.
  - Dùng `MicrosoftGraphOTPProvider` (từ `chatgpt_gpm_direct_reg.py`).
- **Pre-validation trước khi chạy batch:**
  - Endpoint refresh token: `https://login.microsoftonline.com/common/oauth2/v2.0/token` với scope `https://graph.microsoft.com/Mail.Read offline_access`.
  - Lọc bỏ các token trả về `AADSTS70000: grant is expired` trước khi duyệt nạp.
- **Bắt OTP chuẩn:**
  - Ghi nhận mốc thời gian `t_send = now(utc) - 15s` ngay trước khi bấm submit email trên form login ChatGPT.
  - Polling Graph API tối đa 8-12 lần (mỗi lần cách 2s), chỉ lấy email có `receivedDateTime > t_send` và tiêu đề chứa `openai` / `chatgpt` để tránh nuốt phải OTP cũ đã hết hạn.

## 4. Định mức phân bổ Proxy trên OmniRoute (Pool Cap)
- **Giới hạn 2 acc / IP:**
  - Kiểm tra bảng `proxy_assignments` (`scope = 'account'`) kết hợp `provider_connections` (`provider = 'chatgpt-web'`, `is_active = 1`).
  - Cổng nào đã có $\ge 2$ tài khoản active thì BỎ QUA HOÀN TOÀN (khóa trần).
  - Cổng có 1 acc chỉ nạp bù đúng 1 acc; cổng có 0 acc nạp đủ 2 acc.
- **Fail-closed Proxy Mapping:**
  - Chỉ kích hoạt `is_active = 1` sau khi đã resolve chính xác `proxy_id` tương ứng trong `proxy_registry` và tạo bản ghi gán cứng trong `proxy_assignments`.
