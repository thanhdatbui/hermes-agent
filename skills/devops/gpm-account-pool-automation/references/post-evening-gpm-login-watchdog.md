# Post-Evening GPM Login Watchdog & Proxy Quota Guard

## 1. Mục đích & Cơ chế hoạt động
Watchdog `post-evening-gpm-login-watchdog` (chạy script `post_evening_gpm_login_watchdog.py`) vận hành trong khung giờ tối (20:15 - 23:45 HCM) để tự động đăng nhập các tài khoản Gmail lên GPMLogin:
- **Tập ứng viên**: Gmail hết hạn `cooldown_7days` hoặc tài khoản `LIVE` trên sheet `Kibe_Farm_S7` đã tạo profile GPM nhưng chưa nạp `omniroute_success`.
- **An toàn mạng (Proxy Quota)**: Giới hạn cứng `MAX_LOGINS_PER_PROXY = 2` (tối đa 2 lần login/cổng proxy/ngày). Mỗi thiết bị (`mid`) tối đa 1 lần login/ngày.

## 2. Ý nghĩa thông báo tổng kết ca tối
Khi watchdog báo về:
```
[LOGIN GPM ĐÊM - TỔNG KẾT] ✓ <success> | ✗ <fail> | proxy_limit 2/port/ngày | Hoàn tất ca tối
```
Điều này mang ý nghĩa:
1. **Hoàn tất ca an toàn**: Không còn tài khoản nào hợp lệ hoặc toàn bộ các cổng proxy tương ứng đã chạm trần `2/port/ngày`. Trạng thái `finished: true` được ghi vào `post_evening_gpm_login_state.json`.
2. **Không phải lỗi crash**: Đây là chốt chặn an toàn (Circuit Breaker) ngăn chặn việc spam login gây cháy dải proxy di động 4G hoặc làm Google cắm cờ (flag/checkpoint) tài khoản farm.

## 3. Các dạng thất bại phổ biến & Cách đối soát
Khi `fail > 0` (hoặc `✓ 0 | ✗ N | proxy_limit 2/port/ngày`):
- **Tài khoản chưa có TOTP 2FA (`totp_secret` rỗng)**: Khi bộ lọc `two_fa` được mở rộng, các tài khoản chưa có Secret Key trên Excel bắt buộc phải xác minh qua S7 thiết bị thật (Google Prompt, OOTP 10 số trong Settings, hoặc SMS OTP SĐT 24). Nếu thiết bị S7 không hiển thị prompt hoặc Playwright chờ quá 180s, script tự động ngắt `TIMEOUT` / `FAILED`.
- **Cơ chế Circuit Breaker của Proxy**: Mỗi lần gọi (kể cả thất bại) đều tính vào `proxy_count[port]`. Khi chạm trần 2 lần/cổng/ngày, watchdog dừng phân bổ cho cổng đó để chống cháy dải proxy di động.
- **Phân loại lỗi chính xác qua 3 nhóm file ảnh trong `debug_screenshots`**:
  1. `oauth_<email>_hard_phone_checkpoint_*.png` (`challenge/iap`): Google phát hiện trình duyệt PC mới chưa có 2FA, đòi SĐT mới vì "hoạt động bất thường". Script kích hoạt Fail-Safe dừng ngay (`PHONE_CHECKPOINT`) để chống spam khóa nick.
  2. `oauth_<email>_timeout_*.png`: Timeout 180s do chờ Google Prompt trên S7 nhưng không có push notification tới máy hoặc challenge không tự giải được.
  3. `oauth_<email>_waiting_otp_24.png`: Màn hình đòi SMS OTP số điện thoại đuôi 24 của Tad, ca đêm chạy tự động không có người trực nhập mã -> `SMS_TIMEOUT`.
- **Cảnh báo bẫy nhận định sai về 2FA vs Session Cookie cũ & Độ Trust thực tế (Account Trust Score)**:
  - Khi thấy tài khoản không có `totp_secret` trên Excel nhưng vẫn login GPM/OmniRoute thành công (ví dụ `cecilssimpsono8a2m`):
    + Nếu profile GPM đó **đã có sẵn session Google sống từ trước (hoặc vừa đăng nhập thành công vào buổi tối trước đó)**: Khi mở lên, Google hiện màn hình **Account Chooser ("Choose an account to continue to OpenAI")**. Script chỉ việc click chọn tên tài khoản là Google cấp Authorization Code ngay, hoàn toàn không đòi mật khẩu, OTP hay checkpoint.
    + **Bản chất kỹ thuật**: Không phải "bắt buộc có 2FA mới login được". Google Risk Engine quyết định mở cửa hoàn toàn dựa trên **Account Trust Score**. Khi Trust cao, tài khoản vào thẳng 100% chỉ bằng Email + Pass mà không đòi 2FA. Khi Trust thấp / tài khoản tĩnh chưa có tương tác hòm thư, Google sẽ bật Hard Checkpoint đòi SĐT.
    + **Chiến lược tăng Trust bền vững trước khi lên GPM**: Cho các tài khoản ngâm trên S7 chạy liên kết ChatGPT (`watchdog_link_chatgpt_idle.py`) qua luồng Direct Email OTP trước. Quá trình nhận email, đọc OTP và sync hòm thư thật trên S7 sẽ bồi đắp Trust Score tự nhiên, tạo bàn đạp để lên GPM mượt mà.
  - **Bẫy nghẽn khi chạy `MAX_WORKERS = 5`**: Khi chạy 5 browser song song qua cụm proxy và cùng bắn callback về OmniRoute `:20129`, tài khoản có session sẵn hoặc vào được đến màn hình consent vẫn có thể bị văng timeout do nghẽn băng thông proxy, trễ callback hoặc tranh chấp lock `oauth_pipeline_status.json.lock`. Khi chạy lại đơn lẻ (1 worker) hoặc hạ về `MAX_WORKERS = 2`, tài khoản sẽ pass ngay lập tức. Cấu hình chuẩn của watchdog này **bắt buộc là `MAX_WORKERS = 2`**.
  - **Phương pháp xác minh chuẩn**: Dùng `winrt_ocr.py` quét ảnh `{email}_success.png` và truy vấn database `Default/History` của Chromium profile để phân biệt rõ: ăn nhờ `Account Chooser` (có sẵn session), đăng nhập thẳng credentials (trust cao), hay ăn nhờ luồng TOTP.
- **Bẫy nuốt log Subprocess**: `post_evening_gpm_login_watchdog.py` dùng `subprocess.run(..., capture_output=True)` nhưng chỉ log `✗ {email}` mà không in `combined` ra stderr khi thất bại. Nguồn bằng chứng gốc duy nhất để biết chính xác lỗi là kiểm tra file ảnh tại `D:\Taadaa\GPM auto\debug_screenshots\`.
- **Quy tắc thứ tự vòng đời (Lifecycle Dependency)**: BẮT BUỘC để watchdog ca sáng (`post-morning-gmail-2fa-watchdog`) kích hoạt Google Authenticator trên điện thoại S7 và lưu `2FA_Secret` vào Excel trước. Khi có `2FA_Secret`, ca tối đăng nhập PC chỉ việc sinh mã TOTP 6 số là qua 100%, không bị Google kích hoạt phone checkpoint.
- **Quy trình đối soát an toàn**:
  1. Kiểm tra `D:\Taadaa\runtime\kibe\cron-state\post_evening_gpm_login_state.json`: xác nhận `finished: true`, danh sách `processed`, và bảng `proxy_count`.
  2. Kiểm tra `D:\Taadaa\GPM auto\config\oauth_pipeline_status.json`: xem tài khoản có bị Google gắn cờ `cooldown_7days` (rrk=77), `wrong_password_or_checkpoint`, hay `ip_cooling_recaptcha`.
  3. Kiểm tra ảnh debug tại `D:\Taadaa\GPM auto\debug_screenshots\`:
     - **Google 2SV Prompt (`oauth_<email>_timeout_*.png`)**: Google yêu cầu xác nhận 2SV qua thiết bị thật (*"Nhấn vào Có trên điện thoại..."*).
     - **Hard Phone Checkpoint (`oauth_<email>_hard_phone_checkpoint_*.png`)**: Google yêu cầu nhập SĐT xác minh danh tính.
     - **reCAPTCHA Cooldown**: Cần hạ nhiệt IP.
  4. Trạng thái sau ca tối: Toàn bộ device lock trên S7 phải được nhả, farm ở trạng thái nghỉ an toàn. Không retry cưỡng bức trong đêm tránh cháy quota và checkpoint hàng loạt.
