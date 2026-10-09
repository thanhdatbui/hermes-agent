# Guard Catch-22, Over-Protection Antipatterns & Passwordless Gmail Missing on Device (2026-10-04)

## 1. Hiện Tượng & Sự Cố (User Incident 2026-10-04)
- Khi máy M3 (Row 8) bị cảnh báo P0 văng tài khoản TikTok `@annhubvqttr`, Coordinator cố gắng thực thi chẩn đoán và chạy script tự động nạp bù `recover_missing_tiktok_login.py`.
- Tuy nhiên hệ thống Guard Controller liên tục ném lỗi chặn đứng mọi hành động:
  - Terminal blocked khi chạy `python D:/Taadaa/tools/...`
  - Báo động cấm thao tác khi chạy `adb shell input keyevent 224` (wake up)
  - Self-protection báo động giả khi đọc file cache hoặc dispatch subagent có chứa chuỗi đường dẫn.
  - Subagent Worker bị khóa Terminal không được chạy script phục hồi.
  - User bực mình chỉ đạo trực tiếp: *"Sửa guard ngu lồn cho tao."*

---

## 2. Phân Tích Các Lỗi Kiến Trúc & Regex Của Guard Controller

### Lỗi 1: Regex Path Thiếu Dấu Hai Chấm Cho Đường Dẫn Tuyệt Đối Windows
- **Vị trí**: Bộ lọc allowlist terminal cho Coordinator.
- **Nguyên nhân**: Pattern regex allowlist case C dùng `[\w\-/\\]+\.py\b`.
  Trong Windows, đường dẫn tuyệt đối bắt đầu bằng ký tự ổ đĩa và dấu hai chấm (ví dụ `D:/Taadaa/...`). Tập ký tự `[\w\-/\\]` **không chứa dấu hai chấm `:`**, dẫn đến việc mọi lệnh `python D:/...` đều bị trượt regex và rơi vào Default-Deny!
- **Khắc phục**: Đổi thành `(?:python(?:\.exe)?\s+(?:-m\s+pytest\b|[a-zA-Z]:[/\\][\w\-/:\\\.]+\.py\b|[\w\-/:\\\.]+\.py\b)|pytest(?:\.exe)?\b)`.

### Lỗi 2: Nhóm Cấm Input Bị Nhét Nhầm `keyevent`
- **Vị trí**: Regex cấm ADB: `\binput\s+(?:tap|swipe|keyevent)\b`.
- **Nguyên nhân**: Thông điệp cảnh báo là "cấm tap/swipe bấm tay thay cho sửa code", nhưng regex lại cấm cả `keyevent`. Các keyevent phần cứng như `224` (bật màn hình), `82` (mở khóa), `3` (Home), `4` (Back), `26` (Power) là các lệnh quản trị thiết bị an toàn, việc cấm chúng làm Coordinator không thể đánh thức điện thoại khi màn hình tắt.
- **Khắc phục**: Sửa regex thành `\binput\s+(?:tap|swipe)\b`, cho phép `keyevent` chạy bình thường.

### Lỗi 3: Self-Protection Quét Chuỗi Quá Rộng
- **Vị trí**: Hàm kiểm tra target nhạy cảm trong plugin hook.
- **Nguyên nhân**: Quét chuỗi thư mục runtime trên MỌI tham số của MỌI tool call (kể cả `read_file`, `delegate_task`). Khi Coordinator đọc cache kết quả tại các thư mục tạm hoặc truyền context có nhắc đến đường dẫn, guard báo động giả và chặn đứng tool call.
- **Khắc phục**: Loại bỏ chuỗi blanket; chỉ bảo vệ các file nhạy cảm thực sự (database, credentials) và chỉ chặn khi tool call là thao tác GHI (`write_file`, `patch`).

### Lỗi 4: Allowlist Của Worker Bị Khóa Cứng Không Cho Cứu Hộ
- **Vị trí**: Hàm validate lệnh terminal cho Worker.
- **Nguyên nhân**: Worker chỉ được phép chạy đúng 4 lệnh: `git status/diff/log`, `adb devices`, `inspect_machine.py <N>`, `pytest`. Toàn bộ các script cứu hộ của Farm (`recover_missing_tiktok_login.py`, `farm_idle_screen_and_app_healer.py`, `sync_farm_account_info.py`) đều bị chặn.
- **Khắc phục**: Mở rộng allowlist cho phép Worker thực thi các script python dưới `D:/Taadaa/tools/` và các lệnh ADB an toàn theo serial máy (`getprop`, `dumpsys`, `screencap`, `pull`, `push`).

---

## 3. Bẫy Ngộ Nhận Gmail DIE Giả Do Biến Môi Trường Kế Thừa
- Khi tài khoản thiếu pass TikTok (`missing_tiktok_pass`), `tiktok_login_v1.py` gọi `check_gmail_live_fast.py` để kiểm tra live mail bằng Playwright.
- Do kế thừa biến môi trường từ tiến trình cha (chứa thư viện `greenlet` bị hỏng extension C), import Playwright ném `ModuleNotFoundError: No module named 'greenlet._greenlet'`.
- Khối `except Exception:` trong `tiktok_login_v1.py` bắt lỗi này và fallback gán hàm trả về `False` (DIE), làm hệ thống ngộ nhận email đã chết và chặn login với RC=2!
- **Khắc phục**: Trong `recover_missing_tiktok_login.py`, bắt buộc tách lập môi trường:
  ```python
  env = os.environ.copy()
  env.pop("PYTHONPATH", None)
  ```

---

## 4. Bẫy OTP Mail Khi Gmail Chưa Đăng Nhập Trên Thiết Bị S7
- **Bản chất**: Tài khoản TikTok passwordless khi đăng nhập bằng email sẽ kích hoạt luồng gửi mã OTP 6 số về Gmail.
- **Hiện trường**: Module `handle_tiktok_email_otp` (`social_reg_v1.py`) được thiết kế để mở ứng dụng Gmail (`com.google.android.gm`) trực tiếp trên điện thoại Samsung S7 và đọc OTP từ thông báo/inbox.
- **Điểm nghẽn**: Nếu tài khoản Gmail mục tiêu chưa từng được đăng nhập vào ứng dụng Gmail trên máy S7 (trên máy chỉ có mail khác), script sẽ quét 4 lần không thấy tài khoản và timeout OTP 150s.
- **Quy tắc xử lý**:
  1. Kiểm tra trước xem tài khoản Gmail đã có trong danh sách tài khoản của máy chưa (`dumpsys account` hoặc mở Gmail switcher).
  2. Nếu chưa có: Phải nạp tài khoản Gmail vào máy trước, HOẶC lấy OTP qua web/GPM, HOẶC đổi tài khoản có sẵn mật khẩu TikTok để vào bằng ID+Pass+2FA TOTP (né 100% bẫy OTP mail).

---

## 5. Tinh Chỉnh Timeout Cho Thiết Bị Galaxy S7
- Samsung Galaxy S7 (Android 8, RAM 4GB) có tốc độ xử lý chậm:
  - Khởi động app TikTok: 30-45s
  - Mỗi lần dump UI XML: 20-30s
  - Kiểm tra live Gmail: ~50s
  - Điều hướng Profile & Switcher: ~120s
- `timeout=300` (5 phút) trong runner là quá ngắn, dễ gây `TimeoutExpired` khi đang thao tác dở.
- Nâng `timeout=600` (10 phút) và luôn truyền `--resume` nếu app TikTok đã mở sẵn trên thiết bị.
