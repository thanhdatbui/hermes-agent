# ChatGPT Web Pool Feeding & GPM Hotmail Lifecycle Architecture

## 1. Cấu trúc Quản trị Pool ChatGPT Web trên OmniRoute (:20129)
- **Định mức Proxy (Cap):** Giới hạn tối đa **2 accounts / 1 proxy IP**. Mỗi account khi nạp vào `provider_connections` (`provider = 'chatgpt-web'`, `is_active = 1`) bắt buộc phải có bản ghi tương ứng trong `proxy_assignments` (`scope = 'account'`, `scope_id = <connection_id>`, `proxy_id = <proxy_id>`).
- **Phân bổ Port:**
  - MobiProxy 4G: Port 5101 – 5138 (`test.taadaa.click`).
  - MikroTik: Port 10001 – 10035 (`mirotik1.taadaa.click`).
- **Worker Concurrency:** Khi chạy tiến trình bóc tách cookie CDP ngầm, giới hạn tối đa `max_workers = 3..5` để tránh bão Chrome ngầm gây nghẽn RAM và tràn timeout proxy 4G.

## 2. Bản chất Vòng đời Hotmail GPM & Phân biệt Đăng ký Thật vs Ảo
- **Thuật ngữ chuẩn xác:** Toàn bộ tài khoản Hotmail trên farm là **MAIL MUA SẴN** (từ các đợt mua `latest_bought_*.txt`). CẤM TUYỆT ĐỐI gọi là "reg Hotmail". Giai đoạn `HOTMAIL_LOGIN` là đăng nhập mail mua sẵn vào GPM profile bằng `mail_password`, sau đó mới đến `CHATGPT_REG`.
- **Dấu hiệu nhận biết acc CHƯA REG ChatGPT:**
  - Khi điền email vào form login OpenAI, nếu màn hình chuyển hướng sang **"Bạn bao nhiêu tuổi?" (`/about-you`)** hoặc `/create-account/password`, đó là màn hình Onboarding tài khoản mới. Điều này chứng minh tài khoản **CHƯA TỪNG được đăng ký ChatGPT trước đó**.
  - Không được nhầm lẫn màn hình `/about-you` với màn hình đăng nhập lại (re-login).
- **Cơ chế OTP Microsoft Graph:**
  - Đối với tài khoản đã đăng ký cần kích hoạt session mới qua `auth.openai.com/email-verification`, OpenAI gửi mã OTP 6 số về hòm thư Hotmail.
  - Sử dụng `MicrosoftGraphOTPProvider` với `refresh_token` và `client_id` từ `gmail_clean_v2.xlsx`.
  - Bắt buộc kiểm tra mốc thời gian `receivedDateTime > t_send` để tránh bốc nhầm mã OTP cũ.

## 3. Cấm Exit Code 0 Bậy bạ (Chống False-Success Supervisor)
- **Lỗ hổng False-Success:** Nếu script con (`chatgpt_gpm_direct_reg.py`) trả về exit code 0 khi danh sách ứng viên rỗng (`candidates = []`) hoặc khi đăng ký thất bại (`FAIL_PASSWORD_NOT_FOUND`, `FAIL_OTP_TIMEOUT`), supervisor cha (`batch_gpm_5profiles_supervisor.py`) sẽ coi `run_cmd` thành công (`proc.returncode == 0`) và tự động đóng dấu `chatgpt_registered_at = now()`, chuyển tài khoản sang `WAIT_7D` rồi `DONE` ảo.
- **Quy chuẩn Exit Code:**
  - Khi gọi cụ thể `--email <email>` mà không tìm thấy ứng viên hợp lệ: BẮT BUỘC exit `1`.
  - Khi bất kỳ ứng viên nào đăng ký không đạt `SUCCESS` hoặc `ALREADY_LOGGED_IN`: BẮT BUỘC exit `1`.

## 4. Lệch Schema Excel giữa Kibe và Admin
- **Hiện trạng:**
  - File Kibe (`D:\OneDrive\TaadaaData\kibe\taikhoan_dat_v2_updated .xlsx`): Có 12 cột, cột 11 (cột L) là `PASS CHATGPT`.
  - File Admin (`D:\OneDrive\TaadaaData\admin\taikhoan_dat_v2_updated .xlsx`): Chỉ có 10 cột, dừng lại ở `device ID` (không có cột 11).
  - File `D:\OneDrive\TaadaaData\admin\gmail_clean_v2.xlsx`: Dù tên là `gmail` nhưng thực tế lưu 100% tài khoản Hotmail mua của cụm Admin kèm token Graph và password mail.
- **Quy tắc xử lý:**
  - CẤM hardcode duy nhất đường dẫn Kibe. Bắt buộc rà soát cả 2 cụm `kibe/` và `admin/`.
  - Khi không tìm thấy cột `PASS CHATGPT`, tự động fallback lấy mật khẩu mail của chính tài khoản Hotmail đó và chuẩn hóa qua `normalize_password`.

## 5. Chống Pattern Footprint Mật khẩu (Cấm Hậu tố Tĩnh)
- **CẤM TUYỆT ĐỐI nối chuỗi cố định:** Cấm dùng hậu tố tĩnh như `@Taadaa2026` hay tên thương hiệu farm cho hàng loạt tài khoản. Đây là pattern footprint cực kỳ lộ liễu khiến bot OpenAI dễ dàng quét trảm hàng loạt.
- **Cơ chế Salt ngẫu nhiên per-account:**
  - Nếu mật khẩu $< 12$ ký tự, sinh salt ngẫu nhiên đa dạng (kết hợp các ký tự đặc biệt `@, #, $, %, !, &, *`, chữ hoa, chữ thường và chữ số riêng biệt theo hash của từng tài khoản).
  - Tự động lưu mật khẩu thực tế vừa tạo vào cột `PASS CHATGPT` của file Excel tương ứng (`save_chatgpt_password_to_excel`).
