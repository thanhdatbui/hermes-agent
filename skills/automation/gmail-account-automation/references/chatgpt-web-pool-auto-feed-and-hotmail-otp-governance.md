# ChatGPT Web Pool Auto-Feed, Proxy Allocation & Hotmail OTP Governance

## 1. Nguyên Tắc Phân Bổ Proxy & Định Mức (Cap 2 Acc / IP)
- **Định mức cứng:** Mỗi proxy active trong `proxy_registry` (MobiProxy 4G `5101–5138` và MikroTik `10001–10035`) chỉ gán tối đa **2 tài khoản `chatgpt-web` active**.
- **Liên kết bắt buộc (`proxy_assignments`):**
  * Mỗi tài khoản nạp vào OmniRoute phải có bản ghi trong bảng `proxy_assignments` với `scope = 'account'`, `scope_id = <connection_id>`, `proxy_id = <proxy_id>` khớp đúng port của profile GPM.
  * Tự động thêm connection ID vào 2 combo định tuyến: `chatgpt-web-pool` và `gpt-web-sol`.
- **Kiểm chứng end-to-end:** Sau khi nạp, gửi request test trực tiếp qua OmniRoute `:20129` trên model `chatgpt-web/gpt-5.6-luna-free` với header `x-omniroute-connection-id: <id>` để xác nhận HTTP 200 OK trước khi bàn giao.

---

## 2. Cạm Bẫy Lọc Ứng Viên: "Profile Tạo Sẵn" vs "Tài Khoản Đã Reg Thật" (Candidate Selection Trap)
- **Hiện tượng lỗi:** Khi quét DB `Profiles` của GPMLogin chỉ theo chuỗi `@hotmail.com`, script bốc nhầm các tài khoản mới chỉ hoàn thành bước tạo profile (`stage: "HOTMAIL_LOGIN"`, chưa từng reg ChatGPT).
- **Hậu quả:** Khi Playwright mở trang login ChatGPT và điền email, OpenAI nhận diện là người dùng mới và chuyển hướng sang `/create-account/password` hoặc đòi tạo mật khẩu mới.
- **Quy tắc bắt buộc:**
  1. **Không bao giờ tin tưởng tên profile đơn thuần:** BẮT BUỘC đối soát với state file supervisor (`batch_gpm_5profiles_supervisor_state.json` ở cả cụm Kibe và Admin).
  2. **Tiêu chí lọc tài khoản đã reg:** Chỉ chấp nhận tài khoản có `stage in ('DONE', 'WAIT_7D', 'CHANGE_INFO')` HOẶC có mốc thời gian `chatgpt_registered_at` hợp lệ.

---

## 3. Cạm Bẫy Profile Trong Thùng Rác (`GroupId == 0` / `PROFILE_IN_TRASH`)
- **Hiện tượng:** Trong database `profile_data.db` của GPMLogin, các profile bị người dùng xóa hoặc ở trạng thái nháp được gán `GroupId = 0`.
- **Hậu quả:** Gọi API `/api/v3/profiles/start/{id}` sẽ văng lỗi `PROFILE_IN_TRASH` hoặc `PROFILE_NOT_FOUND`, làm nghẽn worker retry nhiều lần.
- **Khắc phục:** Luôn bọc điều kiện `WHERE GroupId != 0` trong mọi câu lệnh query profile GPM.

---

## 4. Cơ Chế Tự Động Kích Hoạt Phiên Hết Hạn Qua Microsoft Graph OTP (Zero-Touch Reauth)
- **Bản chất kỹ thuật:** Tài khoản ChatGPT đăng ký bằng Hotmail sau hơn 14 ngày không dùng sẽ bị hết hạn session token trên trình duyệt. Khi mở lại, OpenAI bắt buộc xác thực danh tính bằng **mã OTP 6 số gửi về hòm thư Hotmail** (`auth.openai.com/email-verification`).
- **Quy trình giải OTP tự động 100% qua Microsoft Graph API:**
  1. **Nạp & Tiền kiểm tra token (Pre-validation):**
     * Đọc `refresh_token` và `client_id` từ `admin/gmail_clean_v2.xlsx` hoặc `kibe/gmail_clean_v2.xlsx`.
     * Chạy request POST tới `https://login.microsoftonline.com/common/oauth2/v2.0/token` để lọc ra danh sách token còn sống (tránh mở profile rồi mới phát hiện token chết).
  2. **Gửi form đăng nhập & lấy mốc thời gian:**
     * Bấm `Log in` trên `https://chatgpt.com/` ➔ Điền email ➔ Lưu mốc thời gian `t_send = now(utc) - 15s` ➔ Bấm Enter để OpenAI gửi mã.
     * Chờ URL chuyển sang `auth.openai.com/email-verification`.
  3. **Polling mã OTP qua Graph API:**
     * Gọi endpoint `https://graph.microsoft.com/v1.0/me/messages?$top=3&$select=id,subject,receivedDateTime`.
     * So khớp email có tiêu đề chứa `openai` hoặc `chatgpt` và thời gian nhận `receivedDateTime > t_send`.
     * Đọc nội dung email và trích xuất mã 6 số qua regex `\b(\d{6})\b`.
  4. **Điền OTP & Vượt Onboarding "About You":**
     * Điền mã vào `input[name="code"]` và bấm nút submit.
     * Nếu OpenAI chuyển hướng sang `/about-you`: Điền Họ tên + Tuổi (>= 18), bấm `Continue` để kích hoạt redirect callback `chatgpt.com/api/auth/callback/openai?...`.
     * Chờ trình duyệt quay lại domain `chatgpt.com` rồi mới bóc tách cookie `__Secure-next-auth.session-token`.
  5. **Đóng profile & Giải phóng RAM:**
     * Đóng profile GPM ngay sau khi lấy token, quét dọn các tiến trình `chrome.exe` mồ côi để tránh cạn kiệt tài nguyên máy.

---

## 5. Kỷ Luật Vận Hành Điều Phối (Coordinator Execution Discipline)
- **Cấm đóng gói base64 script trong terminal:** Việc bọc mã Python thành chuỗi base64 chạy qua `python -c "exec(...)"` kích hoạt cơ chế bảo vệ Guard của hệ thống, gây block và bật approval prompt làm đứt quãng luồng tự động.
- **Thực thi trước, báo cáo bằng chứng sau:** Khi user giục tiến độ ("Vibe O(1), bực=làm ngay"), khởi chạy background process ngay lập tức, theo dõi qua `process(action='poll')` và cơ sở dữ liệu `storage.sqlite`, tuyệt đối không phân trần hay giải thích dông dài trước khi có kết quả thực tế.
