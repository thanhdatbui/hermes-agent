# Pitfalls: Phân tích lỗi đăng nhập TikTok & Hotmail trên Phone Farm (17/09/2026)

## 1. Lỗi suy luận mù khi đọc ảnh hiện trường (OCR Readback Failure)
- **Triệu chứng:** Agent chụp ảnh màn hình lỗi nhưng chỉ xem cây XML Accessibility của Android rồi tự suy diễn: "Nút Tiếp bị mất callback JavaScript trong Webview", "Nút bấm bị kẹt", trong khi thực tế trên ảnh màn hình hiển thị thông báo chữ đỏ:
  `Số lần nhập sai tài khoản hoặc mật khẩu đã đạt giới hạn. Hãy thử lại sau 29m.` hoặc `Mật khẩu sai`.
- **Nguyên nhân gốc rễ:** Nhiều màn hình xác minh của TikTok là Webview / Canvas hoặc render text thông báo dạng toast/canvas overlay không đẩy vào cây accessibility XML node.
- **Kỷ luật bắt buộc (Gate 6 OCR Readback):**
  1. Sau khi screencap, **BẮT BUỘC** gọi tool WinRT OCR (`python .../winrt_ocr.py <image_path>`) bóc tách 100% text trên ảnh.
  2. Quét các từ khóa đỏ: `nhập sai`, `giới hạn`, `thử lại sau`, `sai mật khẩu`, `mật khẩu không đúng`, `phiên đã hết hạn`.
  3. Trích xuất nguyên văn thông báo lỗi từ OCR vào báo cáo trước khi đưa ra kết luận. CẤM suy đoán mò khi chưa đọc text ảnh.

## 2. Lỗi logic đè pass ảo trong `social_reg_v1.py` (User Rule 2026-08-16)
- **Triệu chứng:** Tài khoản TikTok sau khi reg lưu trong Excel có pass phức tạp (vd: `FN4WstbpPd8O@9Y`), nhưng khi đăng nhập lại trên máy khác thì TikTok báo `Sai tài khoản hoặc mật khẩu`.
- **Nguyên nhân gốc rễ:**
  - TikTok khi đăng ký có nhiều đợt skip qua bước tạo pass (vào thẳng Profile bằng email/OTP).
  - Ở nhánh đăng ký (dòng 8676), rule đã ép: `if not password_written: tiktok_pw = ""`.
  - Nhưng ở hàm lưu Excel `ensure_profile_completed_and_track` (dòng 5538 cũ), có dòng fallback:
    `tiktok_pw = tiktok_pw or (make_tiktok_password(mail_pw) if mail_pw else "")`.
  - Dòng này tự động bịa ra một mật khẩu random ngẫu nhiên và ghi đè vào cột `PASS` của Excel, trong khi server TikTok chưa từng được set mật khẩu này.
- **Khắc phục:**
  - Xóa bỏ triệt để `make_tiktok_password` trong hàm ghi tracking. Nếu không qua bước tạo pass thật, cột `PASS` **BẮT BUỘC ĐỂ TRỐNG (`""` / `None`)**.
  - Với tài khoản trống pass: Phải đăng nhập bằng mã OTP email hoặc link khôi phục, sau đó vào `Cài đặt > Tài khoản > Mật khẩu` để tạo mật khẩu lần đầu.

## 3. Khôi phục Hotmail bằng Email khôi phục `thanhdatbui1995@gmail.com`
- **Triệu chứng:** Hotmail khi đăng nhập trên máy mới bị báo `Mật khẩu không đúng với tài khoản Microsoft của bạn` do trước đó đã chạy flow đổi pass định kỳ (`hotmail_change_info.py`) nhưng bị gián đoạn ghi file.
- **Cơ chế khôi phục tự động có sẵn:**
  - Hộp thư khôi phục mặc định: `thanhdatbui1995@gmail.com`.
  - Cấu hình qua env: `OTP_MAIL_USER="thanhdatbui1995@gmail.com"` và `OTP_MAIL_APP_PASSWORD`.
  - Module `flows.hotmail_recovery.poll_latest_otp(not_before_ts=...)` tự động kết nối IMAP `imap.gmail.com:993` để quét mã OTP 6 số từ Microsoft gửi về.
  - Sau khi lấy OTP qua IMAP, điền vào web Microsoft để đặt lại mật khẩu mới đồng bộ.
