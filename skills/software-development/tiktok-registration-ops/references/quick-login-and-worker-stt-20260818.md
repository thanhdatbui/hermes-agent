# TikTok Reg Quick-Login & Worker STT Fixes (2026-08-18)

## 1. Màn hình "Tiếp tục với tên @username" (Quick-Login / One-tap Login)
- **Triệu chứng**: Khi script mở dropdown tài khoản -> tap "Thêm tài khoản", TikTok không mở thẳng form chọn "Dùng số điện thoại / Email" mà hiện màn hình đăng nhập nhanh với nút đỏ lớn *"Tiếp tục với tên @username"* và dòng liên kết xám *"Sử dụng tài khoản khác"*.
- **Hậu quả cũ**: Script tìm nút "Dùng SĐT/Email" không thấy -> báo lỗi `[06] Không thấy màn chọn phương thức đăng nhập` hoặc `[06_email_option]`.
- **Cách xử lý**:
  - Khi gặp màn hình này (có text `tiep tuc voi ten` hoặc `su dung tai khoan khac`):
  - Tap vào liên kết `find_text_tap(device_id, "Sử dụng tài khoản khác", "Su dung tai khoan khac", "Use another account")` để mở danh sách phương thức đăng nhập.

## 2. Truyền tham số STT cho Worker trong `_run_all_targets.py`
- `build_child_command` trong `_run_all_targets.py` phải truyền `str(target["stt"])` (số nguyên STT) thay vì truyền serial vào vị trí tham số thứ 2 của `social_reg_v1.py`, tránh lỗi `Không có STT <serial>`.

## 3. ATX-Agent Primary UI XML
- Luôn duy trì ATX-Agent (port 7912) làm PRIMARY đọc UI XML toàn farm.
- Khi bị timeout uiautomator dump, restart ATX-Agent:
  - `monkey -p com.github.uiautomator 1`
  - `/data/local/tmp/atx-agent server -d`
