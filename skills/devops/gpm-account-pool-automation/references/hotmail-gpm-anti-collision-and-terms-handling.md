# Hotmail GPM Lifecycle Scanner & Multi-Cron Synchronization Rules

## 1. Per-Profile Mutex Lock (Anti-Collision across Crons)
- **Vấn đề**: Khi nhiều cron chạy đồng thời (cron nuôi Gmail, cron Hotmail supervisor, cron sync...), nếu 2 cron cùng mở một GPM profile sẽ gây xung đột WebSocket/CDP, crash profile hoặc lỗi session.
- **Giải pháp**:
  - Dùng mutex lock nguyên tử tại: `D:\Taadaa\runtime\kibe\cron-state\profile_locks\<profile_id>.lock`.
  - Trong `gpm_client.py`:
    - `start_profile(profile_id)`: Bắt buộc gọi `acquire_profile_lock(profile_id)`. Nếu profile đang bị khóa bởi tiến trình khác -> raise `RuntimeError: GPM profile is locked by another process`.
    - `stop_profile(profile_id)`: Trong khối `finally` luôn gọi `release_profile_lock(profile_id)`.
    - Tự động auto-heal: Thu hồi lock nếu lock file quá 30 phút hoặc tiến trình sở hữu (`pid`) không còn tồn tại trên Windows.
  - Trong supervisor: Trước khi chọn ứng viên, kiểm tra `is_profile_locked(profile_id)`. Nếu đang bị khóa thì tự động bỏ qua để chọn nick khác ngay trong cùng tick.

## 2. Quy tắc Cooldown 24h theo LOẠI THAO TÁC trên từng IP (Proxy Port)
- **Quy tắc**:
  - **CÙNG LOẠI THAO TÁC**: Trong vòng 24h, 1 IP/Proxy chỉ được thực hiện tối đa 1 nick cho cùng 1 loại hành động (ví dụ `CHATGPT_REG` hoặc `HOTMAIL_LOGIN`).
  - **KHÁC LOẠI THAO TÁC**: 1 IP/Proxy vẫn được chạy các script khác loại trong vòng 24h thoải mái (ví dụ vừa reg ChatGPT xong vẫn có thể chạy Codex OAuth hoặc Change Info cho nick khác).
- **Lưu trữ**: Ghi nhận trong state `ip_action_history[port][stage] = timestamp`.

## 3. Microsoft Account & Hotmail Interstitial Handlers (GPM Playwright)
- **Cookie Consent Banner**:
  - Microsoft hiển thị banner "We use optional cookies... Accept / Reject / Manage cookies".
  - Bắt buộc click "Accept" qua các selector: `button:has-text('Accept')`, `button:has-text('Chấp nhận')`, `#acceptButton`, `#onetrust-accept-btn-handler`. Dùng `.first.click(force=True)`.
- **Màn hình cập nhật Điều khoản (Terms Accrue)**:
  - URL: `https://account.live.com/tou/accrue?...`
  - Tiêu đề: *Chúng tôi đang cập nhật các điều khoản của mình* / *We're updating our terms*.
  - Nút chuyển tiếp hiển thị là chữ **"Tiếp"** (không phải "Tiếp tục" hay "Tiếp theo").
  - Selector cần bắt: `.btn-primary`, `input[value*='Tiếp']`, `button:has-text('Tiếp')`, `input[type='submit']`, `#iNext`.
- **Kiểm tra URL hoàn tất đăng nhập**:
  - Không dùng phép kiểm tra thô `"login.live.com" in url` vì trang `account.live.com/tou/accrue` chứa query param `ru=https://login.live.com/...`.
  - Phải phân tích bằng `urllib.parse.urlparse`:
    ```python
    p_netloc = urlparse(url).netloc.lower()
    p_path = urlparse(url).path.lower()
    if p_netloc in ["account.microsoft.com", "outlook.live.com"] or (p_netloc == "account.live.com" and p_path not in ["/", "/login.srf"]):
        logged_in = True
    ```

## 4. Phân biệt cột Mật khẩu trong Workbook
- **`taikhoan_dat_v2_updated .xlsx` (sheet `Tài Khoản`)**:
  - Cột 3: `PASS` -> Mật khẩu TikTok (cấm dùng cho mail).
  - Cột 6: `PASS MAIL` -> Mật khẩu Hotmail/Gmail.
  - Cột 11: `PASS CHATGPT` -> Mật khẩu chuyên dụng đăng ký ChatGPT độc lập.

## 5. Nguyên tắc Điều phối: Combo [Login Hotmail -> Reg ChatGPT] Trọn Gói 1 Lượt
- **CẤM TUYỆT ĐỐI**: Chạy login hàng loạt toàn bộ nick rồi mới quay lại reg ChatGPT sau.
- **Quy tắc 1 lượt trọn gói per-account**:
  - Khi một worker nhận nick ở stage `HOTMAIL_LOGIN`:
    1. Tạo GPM profile (nếu chưa có) + gán proxy S7 tương ứng.
    2. Đăng nhập Hotmail qua Playwright.
    3. Ngay khi Hotmail login thành công, **chạy tiếp ngay lập tức bước đăng ký ChatGPT (`CHATGPT_REG`)** trên chính profile đó.
    4. Hoàn tất cả 2 bước mới chuyển sang trạng thái ngâm `WAIT_24_48H` (chờ Codex OAuth).
    5. Đóng GPM profile trong khối `finally`.
- **Bảo toàn slot worker (tối đa 5 worker)**:
  - Hàm `select_candidates`: Tuyệt đối không chọn các nick đang ngâm chưa tới hạn (`WAIT_24_48H` chưa đủ 24h, `WAIT_7D` chưa đủ 7 ngày). 5 slot worker chỉ dành cho nick có hành động cần thực thi ngay.

## 6. Nguồn Credential Đa File cho Hotmail Graph API OTP
- **Vấn đề**: File `hotmail_input.txt` chỉ chứa 30 tài khoản ban đầu.
- **Giải pháp**: Quét hợp nhất qua cả 4 file nguồn trong `D:\Taadaa\Hotmail\`:
  1. `hotmail_input.txt`
  2. `latest_bought_70.txt`
  3. `hotmail_all_60_bought.txt`
  4. `latest_bought_8_m76_79.txt`
  (Tổng cộng 144 tài khoản Hotmail có đầy đủ OAuth token để nhận mã OTP qua Microsoft Graph API).
- Trong supervisor: Ưu tiên sắp xếp (`sorted`) các tài khoản có sẵn OAuth token lên đầu hàng đợi để quy trình [Login Hotmail -> Reg ChatGPT] hoàn tất tự động 100% không bị ngắt quãng.

## 7. Codex OAuth Verification: Session-Based vs Google SSO Phone Gate & Ghost Form Trap
- **Xác thực qua Session ChatGPT có sẵn (Pass 100% không SMS)**:
  - Khi profile GPM mở lên, OpenAI nhận diện được session ChatGPT đang sống (`choose-an-account` / `Welcome back`).
  - Script tự click chọn thẻ tài khoản -> Click `Continue / Authorize`.
  - Callback port 1455 nhận mã Authorization Code ngay lập tức. Không bao giờ hỏi số điện thoại hay tốn SIM.
- **Bẫy Form Ma khi Văng Session (Ghost Form Trap -> invalid_auth_step)**:
  - Nếu profile GPM bị văng session ChatGPT (`chatgpt.com` hiện nút Đăng nhập), URL nạp OAuth Codex sẽ redirect về `https://auth.openai.com/log-in`.
  - Nếu script tự ý fallback `page.goto("https://auth.openai.com/add-phone")`, OpenAI chỉ hiển thị giao diện React vỏ rỗng (không có transaction xác thực backend). Khi điền số điện thoại và bấm submit, backend lập tức từ chối và báo lỗi `Bước ủy quyền không hợp lệ (invalid_auth_step)`.
  - Quy chuẩn: Trước khi ver số, BẮT BUỘC kiểm tra session ChatGPT. Nếu bị văng session, phải thực hiện re-login (qua Hotmail Graph API OTP hoặc Password) để khôi phục session trước khi nạp link OAuth.
- **Bẫy Google SSO (Phone Gate)**:
  - Nếu profile bị mất session ChatGPT cũ mà bấm vào `Tiếp tục với Google` (Google SSO), OpenAI lập tức chuyển hướng sang `https://auth.openai.com/add-phone` (*Cần có số điện thoại - OpenAI*) và bắt nhập số điện thoại nhận SMS.
  - **Bài học xương máu**: CẤM dùng Google SSO để đăng nhập OpenAI trong luồng OAuth Codex. Chỉ thực hiện khi profile đang giữ session sống hoặc đăng nhập bằng Email/Password/OTP trực tiếp.
- **Tài khoản Passwordless vs Pass Mail**:
  - Nhiều tài khoản khi đăng ký trước đây được OpenAI chuyển thẳng từ nhập Email sang bước nhập OTP (`Mã xác minh tạm thời`) mà không có form tạo Password.
  - Mật khẩu hòm thư Gmail/Hotmail KHÔNG PHẢI mật khẩu ChatGPT. Không được tự ý lấy `PASS MAIL` gõ vào form password của OpenAI khi re-login.

## 8. Quy Trình Thay Thế Hotmail Mất Pass & Migration State Supervisor (User Directive 2026-10-01)
- **Bối cảnh**: Khi phát hiện tài khoản Hotmail cũ bị mất mật khẩu web (`PASS MAIL` = `None`) và không thể tìm thấy trong lịch sử đơn mua BoxTaiKhoan, việc cố thử đăng nhập GPM sẽ gây lỗi sai pass liên tục và rơi vào `BLOCKED`.
- **Chỉ đạo xử lý**:
  1. Cấp Hotmail mới toanh có Graph API OAuth2 token từ kho (`hotmail_input.txt` hoặc `latest_bought_*.txt`).
  2. **Đồng bộ 3 điểm dữ liệu**:
     - *Excel (`taikhoan_dat_v2_updated .xlsx`)*: Tạo bản backup. Cập nhật `GMAIL` = email mới, `PASS MAIL` = pass mail mới, giữ nguyên TikTok username, TikTok PASS và 2FA secret.
     - *Supervisor State (`batch_gpm_5profiles_supervisor_state.json`)*: Đổi key từ `M<N>:<old_email>` sang `M<N>:<new_email>`. Cập nhật `email`, `mail_password`, `profile_name`. Gán `stage = "HOTMAIL_LOGIN"`, `status = "PENDING"`. BẮT BUỘC reset `last_result` thành:
       `{"key": new_key, "status": "PENDING", "stage": "HOTMAIL_LOGIN", "next_stage": "HOTMAIL_LOGIN"}`
       (Tránh để sót kết quả `FAILED` cũ làm sai lệch báo cáo audit).
     - *Input Pool (`hotmail_input.txt`)*: Xóa dòng email vừa sử dụng để chống cấp trùng.
  3. **Đổi email liên kết trên TikTok thiết bị vật lý**:
     - Vào TikTok Settings -> Tài khoản -> Thông tin người dùng -> Email -> Thay đổi email.
     - Vượt gate xác minh danh tính bằng **2FA Authenticator (TOTP)** với secret có sẵn trong Excel (`pyotp.TOTP(secret).now()`), hoàn toàn không cần truy cập hòm thư Hotmail cũ.
     - Nhập Hotmail mới -> Bấm Gửi mã -> Đọc OTP 6 số qua Microsoft Graph API để xác nhận liên kết.
