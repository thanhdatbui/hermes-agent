# Pitfalls: Gmail Newsletter Warmup & Checkmail.live Automation

## 1. Newsletter Warmup False-Positive (Cloudflare Block)
- **Triệu chứng:** Script Python gửi HTTP POST đơn thuần (`urllib.request.urlopen`) tới các endpoint newsletter công khai (như Cooperpress, Substack, v.v.) nhận được status code `200 OK` nhưng không có email chào mừng nào gửi về hòm thư Gmail.
- **Nguyên nhân cốt lõi:** Các endpoint newsletter hiện đại đều được bảo vệ bởi Cloudflare Bot Management / Turnstile challenge. Khi gửi request không có trình duyệt thực, Cloudflare trả về mã `200` kèm trang HTML "Just a moment..." chứa thử thách JavaScript/Captcha, chứ server newsletter chưa hề tiếp nhận hay đăng ký email.
- **Hệ quả:** Script ghi nhận `signed: True` giả tạo, nhưng thực tế hộp thư Gmail vẫn hoàn toàn trống trơn (Ghost / No-activity).
- **Quy tắc:**
  1. Tuyệt đối không dựa vào HTTP status code `200` của `urllib` để khẳng định đăng ký newsletter thành công.
  2. Bắt buộc kiểm tra bằng chứng thực tế tại đích đến: Kiểm tra hòm thư có thư gửi về thật hay không (`dumpsys` / UI dump / IMAP).
  3. Với Gmail mới reg, chiến lược an toàn và bền vững nhất là để tài khoản ngâm tự nhiên $\ge 24-48\text{h}$ trên thiết bị Android S7 kèm telemetry của Google Play Services, thay vì cố tình spam form newsletter bên ngoài bị Cloudflare chặn.

## 2. Tự động hóa Checkmail.live (Session & Auth Gate)
- **Triệu chứng:** Sử dụng Playwright / Chrome mở `https://checkmail.live/` điền email nhưng nút `#btn-check` bấm không chạy, hoặc kết quả `Live: 0, Die: 0, Total: 0` không thay đổi.
- **Nguyên nhân cốt lõi:**
  - Trang `checkmail.live` yêu cầu phiên đăng nhập hợp lệ và có API key (`#api-key`). Nếu không đăng nhập hoặc session hết hạn, hàm JavaScript `CheckEmail()` lập tức `alert('You are not logged in')` và hủy kiểm tra.
  - Sử dụng chung `user_data_dir` giữa các tiến trình song song dễ gây xung đột khóa SQLite (`Failed to decrypt: Key not valid for use in specified state` / Lock conflict).
- **Quy tắc:**
  1. Luôn sử dụng runner chuẩn có tự động tái tạo session / đăng nhập tài khoản tạm thời (`run_checkmail_kibe_farm.py` với `ensure_logged_in_page()`).
  2. Kiểm tra sự tồn tại của `#api-key` trước khi gọi `CheckEmail()` hoặc bấm `#btn-check`.
  3. Khi một tài khoản Gmail bị Google yêu cầu nhập số điện thoại (`challenge/iap` / Phone Checkpoint), trên `checkmail.live` sẽ được phân loại chính xác là **DIE**. Cần loại bỏ ngay khỏi danh sách tài khoản active (`gmail_clean_v2.xlsx`) để tránh làm nghẽn các batch vận hành kế tiếp.
