# TikTok Reg Ops Lessons & Farm Rules Updates (2026-08-21)

## 1. Password Policy khi Reg TikTok
- Đối với các flow đăng ký/đăng nhập TikTok đi qua OTP / email-only mà **không xuất hiện màn hình đặt mật khẩu**:
  - **Bắt buộc để trống cột PASS (`None`)** trong file tracking `taikhoan_dat_v2_updated .xlsx`.
  - **Tuyệt đối cấm** lưu mật khẩu ngẫu nhiên (để sau này còn vào TikTok cài đặt mật khẩu thủ công/bằng tool).

## 2. Quy tắc Device Lock khi Reg Batch
- **Chỉ nhả lock** đối với các máy hoàn thành thành công (`SUCCESS` và đã verified ghi kết quả vào workbook).
- **Các máy bị lỗi, timeout hoặc kẹt:** Phải **giữ nguyên lock ở trạng thái `blocked`** để bảo vệ hiện trường, cấm tự động nhả lock làm các cron/tool khác can thiệp.

## 3. Ảnh báo cáo lỗi thiết bị
- Khi chụp ảnh hiện trường máy lỗi gửi user, bắt buộc phải vẽ **Banner màu đỏ ở đầu ảnh** ghi rõ `[MAY XX] - HH:MM DD/MM` (sử dụng PIL ImageDraw tương tự hệ thống auto-recovery).

## 4. Module Check Gmail Live (từ repo `add mail khoi phuc` / `automation_core.google_health`)
- Khi Gmail không nhận được mã OTP hoặc nghi ngờ mail chết:
  1. Mở Gmail → Tap Avatar → Bấm **"Quản lý Tài khoản Google của bạn"**.
  2. Nếu xuất hiện màn hình *"Hoàn tất đăng nhập để tiếp tục"* → Bấm nút **"Đăng nhập"** → Bấm **"TIẾP THEO"**.
  3. Nếu màn hình xuất hiện **"Xác nhận bạn không phải là rô-bốt / reCAPTCHA"** $\rightarrow$ Mail đã chết, gọi `cleanup_blocked_captcha_account` để xóa tài khoản khỏi máy và cập nhật bảng tính.

## 5. Bắt buộc đọc UI qua ATX-Agent Primary (Port 7912)
- Cấm tuyệt đối chạy shell `uiautomator dump` gây lỗi Exit 137 / treo máy.
- Cấm tap tọa độ pixel mù, mọi thao tác phải dựa trên bounds chính xác từ XML của ATX-agent.
