# ChatGPT Web Pool Feeding: Registration State Taxonomy & GPM Trash Trap

## 1. Phân biệt Bản chất Tài khoản Đã Reg vs Chưa Reg ChatGPT
- **Dấu hiệu `/about-you` ("Bạn bao nhiêu tuổi?" / "How old are you?"):**
  - Khi điền email vào form đăng nhập trên ChatGPT Web (`chatgpt.com`), nếu OpenAI chuyển hướng sang `auth.openai.com/about-you` đòi điền Họ tên và Tuổi, đây là **BẰNG CHỨNG 100% TÀI KHOẢN ĐÓ CHƯA HỀ HOÀN TẤT ĐĂNG KÝ CHATGPT TRƯỚC ĐÂY**.
  - Đây là luồng New User Onboarding cho tài khoản mới tinh, **TUYỆT ĐỐI KHÔNG ĐƯỢC NGỘ NHẬN** là bước xác minh danh tính hay re-login challenge của tài khoản cũ.
  - CẤM bốc các profile đang ở giai đoạn khởi tạo ban đầu (`stage: "HOTMAIL_LOGIN"`, chưa có mốc thời gian hoàn tất `chatgpt_registered_at` hoặc chưa hoàn tất quy trình `DONE`) đem đi nạp pool `chatgpt-web` vì chắc chắn sẽ kẹt ở form tạo tài khoản mới.
- **Dấu hiệu tài khoản đã đăng ký thật sự:**
  - Nếu session cookie còn sống: Truy cập `https://chatgpt.com/` vào thẳng giao diện chat, cookie `__Secure-next-auth.session-token` sẵn sàng trong browser context (độ dài ~8.000 - 11.000 ký tự).
  - Nếu session cookie hết hạn: OpenAI yêu cầu nhập mã OTP 6 số qua email (`auth.openai.com/email-verification`). Sau khi nhập đúng OTP sẽ vào thẳng giao diện chat hoặc yêu cầu mật khẩu cũ đã đặt, không văng sang trang khai báo tuổi nếu tài khoản đã tồn tại.

## 2. Bẫy Profile trong Thùng Rác GPMLogin (`GroupId == 0` / `PROFILE_IN_TRASH`)
- **Cơ chế lưu trữ của GPMLogin:**
  - Trong bảng `Profiles` của SQLite database `profile_data.db` (`C:/Users/<User>/AppData/Local/Programs/GPMLogin/profile/profile_data.db`), các profile đã bị xóa hoặc chuyển vào thùng rác vẫn tồn tại dòng dữ liệu nhưng có thuộc tính `GroupId = 0`.
  - Nếu query trực tiếp bằng SQL (`SELECT Id, Name FROM Profiles WHERE Name LIKE ...`) mà bỏ qua trường `GroupId`, khi gọi API khởi động `GET /api/v3/profiles/start/{id}` GPM sẽ văng lỗi `PROFILE_IN_TRASH`.
  - Việc này kích hoạt cơ chế retry mù (retry 3 lần với sleep 2s) gây nghẽn toàn bộ luồng xử lý và làm timeout tiến trình worker.
- **Quy chuẩn truy vấn an toàn:**
  - Mọi câu lệnh SQL đọc candidate profile từ `profile_data.db` BẮT BUỘC có điều kiện:
    ```sql
    SELECT Id, Name FROM Profiles WHERE GroupId != 0 AND ...
    ```

## 3. Pre-Validation Refresh Token Microsoft Graph API trước khi chạy Batch
- **Nguyên nhân Timeout khi bốc OTP:**
  - Khi tài khoản Hotmail ngâm lâu (> 14-30 ngày), nhiều `refresh_token` lưu trong các workbook (`gmail_clean_v2.xlsx`) bị hết hạn phiên cấp quyền từ phía Microsoft (`AADSTS70000: The user could not be authenticated as the grant is expired`).
  - Nếu chạy luồng worker nạp mà không kiểm tra token trước, worker sẽ kích hoạt gửi OTP từ OpenAI rồi ngồi chờ vô vọng (timeout 60-90s) vì không thể kết nối vào Graph API để đọc hòm thư.
- **Quy trình Pre-validation O(1) đa luồng:**
  - Trước khi khởi động trình duyệt GPM, chạy kiểm tra nhanh `ThreadPoolExecutor(max_workers=25)` gửi POST refresh token tới endpoint:
    `https://login.microsoftonline.com/common/oauth2/v2.0/token`
    với `scope="https://graph.microsoft.com/Mail.Read offline_access"`.
  - Chỉ giữ lại những tài khoản trả về `HTTP 200` vào danh sách xử lý OTP. Tài khoản trả về 400 (`invalid_grant`) phải loại trừ ngay từ đầu.
- **Lọc OTP chuẩn theo mốc thời gian:**
  - Ghi nhận `t_send = datetime.now(timezone.utc) - timedelta(seconds=15)` trước khi nhấn Enter điền email.
  - Khi bóc tách danh sách thư qua Graph API (`$top=3`), chỉ nhận email có `receivedDateTime > t_send` và tiêu đề chứa `openai` / `chatgpt` để tránh lấy nhầm OTP của các phiên đăng nhập cũ.

## 4. Kỷ luật Quản lý Trần Proxy (Pool Density Cap Invariant)
- **Định mức 2 acc / 1 IP:**
  - Đối soát giữa `proxy_registry` (`status='active'`) và `proxy_assignments` (`scope='account'`, `pc.is_active=1`).
  - Khi một port proxy đã có đủ $\ge 2$ tài khoản active, BẮT BUỘC gạch tên port đó khỏi danh sách cần nạp (khóa trần, không nạp thêm).
  - Port có 1 acc chỉ nạp bù đúng 1 acc; port có 0 acc nạp đúng 2 acc.
- **Fail-closed Binding:**
  - Chỉ cập nhật `is_active = 1` trong `provider_connections` sau khi đã resolve thành công ID proxy trong `proxy_registry` và tạo liên kết thành công trong `proxy_assignments`.
