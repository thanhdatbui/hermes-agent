# Hotmail Token Graph API OTP & Fake Password Triage (2026-10-10)

## 1. Bản chất sự cố "Mật khẩu sai" trên nick cũ (Fake Password trong Tracking)
- **Hiện tượng**: Chạy login bằng username/email + mật khẩu TikTok lưu trong Excel (`taikhoan_dat_v2_updated .xlsx` hoặc `taikhoan_run_safe.xlsx`) báo `Mật khẩu sai` / `AUTH_BLOCKED`.
- **Nguyên nhân gốc**: 
  - Các nick đăng ký qua luồng Email OTP (đặc biệt là Hotmail/Outlook) thường được TikTok cho vào thẳng trang chủ sau khi nhập OTP, hoàn toàn không có bước tạo mật khẩu (`Không có màn password (flow email-only / OTP), bỏ qua`).
  - Code đăng ký cũ trước ngày 30/09/2026 dính lỗi fallback: khi không có mật khẩu thật, code tự gọi `make_tiktok_password(mail_pw)` bịa ra mật khẩu ngẫu nhiên rồi lưu vào file Excel như thể đã tạo pass.
- **Quy tắc xử lý**:
  - Khi gặp lỗi sai pass trên nick reg bằng Hotmail/OTP, **CẤM** suy đoán đổi pass hay thử lại pass trong Excel.
  - BẮT BUỘC chuyển sang cờ đăng nhập bằng OTP: `python tiktok_login_v1.py <STT> --email <target> --otp-only --ss`.

## 2. Thứ tự ưu tiên đọc OTP Hotmail / Outlook
Theo đúng chỉ đạo của User: **Kiểm tra mail có token Graph API thì dùng PC đọc, không có token mới đọc từ app Outlook trên điện thoại**.
1. **Kiểm tra Token Graph API (Ưu tiên số 1 - Đọc qua PC)**:
   - Nguồn token: `~/.hermes/hotmail_tokens/<mailbox>.token`, `HOTMAIL_TOKEN_LIST`, hoặc các file mua mail tại `D:/Taadaa/Hotmail/hotmail_all_60_bought.txt`.
   - Nếu tìm thấy `refresh_token` và `client_id`: Lưu token vào `~/.hermes/hotmail_tokens/<mailbox>.token` (định dạng: `<refresh_token> <client_id>`).
   - Gọi `hotmail_provider.read_tiktok_otp_from_graph_token(serial, email)` để đọc OTP trực tiếp qua PC.
   - **CẤM TUYỆT ĐỐI mở app Outlook trên điện thoại** khi hòm thư đã có token Graph API (để tránh làm ẩn/văng ứng dụng TikTok đang chờ OTP).
2. **Fallback đọc qua App Outlook trên điện thoại (Ưu tiên số 2)**:
   - CHỈ áp dụng khi hòm thư hoàn toàn không có token Graph API.
   - Mở app Outlook (`com.microsoft.office.outlook`), kiểm tra hộp thư đến và trích xuất mã OTP 6 số.

## 3. Cạm bẫy Samsung Keyboard Onboarding văng app
- **Hiện tượng**: Sau khi bấm chọn "Sử dụng số điện thoại/email/tên người dùng", script log `[keyboard] com.sec.android.inputmethod onboarding active -> sending BACK keyevent 4`, sau đó script báo lỗi không tìm thấy ô Email vì TikTok đã bị văng về Launcher.
- **Nguyên nhân**: Package `com.sec.android.inputmethod` là bàn phím mặc định của Samsung, luôn xuất hiện trong cây giao diện khi bàn phím mở. Nếu hàm `dismiss_samsung_keyboard_tutorial` chỉ kiểm tra package này rồi gửi phím `BACK` thì sẽ đóng luôn giao diện đăng nhập TikTok.
- **Khắc phục**: CHỈ gửi `BACK` khi thấy rõ id onboarding cụ thể (như `skipButton`), không được kiểm tra chung chung `com.sec.android.inputmethod`.

## 4. Kỷ luật Device Lock khi canh máy rảnh
- Khi user chỉ đạo "Canh máy rảnh thì chạy":
  - Kiểm tra `~/.codex/device-locks/machine_<N>.lock.json`. Nếu tiến trình khác (như `tiktok-add-bao-mat-f2a`, ca nuôi feed) đang giữ lock, **CẤM** cướp lock hay force-stop process.
  - Chạy qua wrapper chuẩn `python D:/Taadaa/tools/with_device_lock.py --machine <N> --timeout 600 -- <cmd>` hoặc chạy nền chờ lock giải phóng sạch sẽ.

## 5. Cạm bẫy màn hình Live Stream (`LivePlayActivity`) sau khi nhập OTP thành công
- **Hiện tượng**: Sau khi điền OTP thành công (`✓ OTP đã nhập xong`), script chạy tiếp 6 vòng `auth round 1/6 ... 6/6` báo `Unknown screen`, sau đó `[9] Wait for login success` timeout 30s và trả về exit code 2 (`PENDING LOGIN`). Tuy nhiên, trên thiết bị nick đã đăng nhập thành công 100%!
- **Nguyên nhân**:
  - Khi TikTok xác thực OTP thành công, thay vì về tab Profile hoặc Home feed có bottom navigation bar, ứng dụng đôi khi tự động mở thẳng một phiên phát trực tiếp (Live Stream: `com.ss.android.ugc.aweme.live.LivePlayActivity`).
  - Giao diện Live Stream chỉ chứa các element như `Chia sẻ`, `Nhập...`, `Mua`, `Follow`, tên nhãn hàng livestream (vd: `Cocoon Vietnam`), hoàn toàn không có `Hồ sơ`, `Profile`, `Dành cho bạn`.
  - Bộ kiểm tra `HOME_HINTS` và `wait_login_success` không nhận diện được màn hình Live nên tưởng lầm đăng nhập thất bại.
- **Cách nhận diện và nghiệm thu**:
  - Kiểm tra focus: `dumpsys window windows | grep mCurrentFocus` thấy `com.ss.android.ugc.aweme.live.LivePlayActivity` $\rightarrow$ Xác nhận TikTok đã đăng nhập thành công.
  - Xử lý thoát Live: Gửi `keyevent 4` (Back) để thoát phòng Live, sau đó gọi `open_profile_root` để điều hướng về tab Hồ sơ và chụp ảnh nghiệm thu.
  - Khi đối soát thành công, tiếp tục kích hoạt ngay runner nạp avatar (`run_tiktok_upload_avatar.ps1`) theo kế hoạch.
