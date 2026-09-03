# TikTok Registration Runner & OTP Pitfalls (2026-09-01)

## 1. Child Worker Target Email Binding (`_run_all_targets.py` -> `social_reg_v1.py`)
- **Triệu chứng:** Detector chọn đúng tài khoản Hotmail cho máy, nhưng khi `social_reg_v1.py` chạy lại bốc trúng tài khoản Gmail cũ từ tháng trước và mở app Gmail tìm OTP dẫn đến lỗi `account list chua thay <email>`.
- **Nguyên nhân:** `_run_all_targets.py` thiết lập `env["SOCIAL_PREFERRED_EMAIL"]` nhưng `build_child_command` không truyền cờ `--email <target_email>`, đồng thời `social_reg_v1.py` chỉ đọc `--email` từ CLI args mà không đọc fallback từ `os.environ.get("SOCIAL_PREFERRED_EMAIL")`. Khi thiếu `--email`, `social_reg_v1.py` duyệt ngược toàn bộ các dòng chưa đăng ký trong `gmail_clean_v2.xlsx` cho STT đó.
- **Quy tắc bắt buộc:**
  * `_run_all_targets.py::build_child_command` BẮT BUỘC thêm `if target.get("email"): cmd.extend(["--email", str(target["email"])])`.
  * `social_reg_v1.py` BẮT BUỘC đọc `preferred_email = os.environ.get("SOCIAL_PREFERRED_EMAIL")` làm fallback khi không có `--email` trong CLI.

## 2. Gmail OTP Reading — System Auto-sync Alert Dialog
- **Triệu chứng:** App Gmail mở lên nhưng bị kẹt ở bước chuyển tài khoản / không vào được inbox (`reason=no_inbox_marker`).
- **Nguyên nhân:** Khi bấm bật auto-sync từ banner, Android hiện dialog xác nhận *"Bật tính năng tự động đồng bộ hóa?"*. Title của dialog này có `resource-id="com.google.android.gm:id/alertTitle"`, trong khi code cũ chỉ tìm `android:id/alertTitle`.
- **Quy tắc bắt buộc:**
  * `_dismiss_gmail_popups` phải tìm `alertTitle` / `alert_title` và text `bat tinh nang tu dong dong bo hoa` để tap `button1` ("Bật").

## 3. TikTok Profile Header Switcher Dropdown (Newer Layouts)
- **Triệu chứng:** Kẹt ở bước [3] không mở được dropdown tài khoản TikTok (`fail_03_account_dropdown`).
- **Nguyên nhân:** Trên các bản TikTok mới, thanh header/display name chuyển sang dùng container `resource-id="com.ss.android.ugc.trill:id/pkh"` và text `resource-id="com.ss.android.ugc.trill:id/pke"`.
- **Quy tắc bắt buộc:**
  * `_try_open_account_dropdown_once` phải bổ sung `pkh` và `pke` vào danh sách sticky bar / header account row.

## 4. Bóc tách bằng chứng lỗi OTP (Evidence-First)
- Tuyệt đối không kết luận "TikTok không gửi OTP" chỉ dựa vào dòng log fallback tóm tắt cuối cùng `(Google Account vẫn LIVE, nhưng TikTok không phát OTP)`.
- Bắt buộc kiểm tra:
  1. Mail đó có thực sự đang đăng nhập trên thiết bị không (`adb shell dumpsys account`).
  2. Log chi tiết trong `stdout.log` có vào được inbox hay bị `account list chua thay <email>` / `no_inbox_marker`.
  3. Kiểm tra ảnh chụp màn hình hiện trường (`screencap`) trước khi báo cáo.
