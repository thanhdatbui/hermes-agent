# TikTok Registration Operations & Rate-limit Cooldown Rules (Update 2026-08-26)

## 1. Single Source of Truth & Quy Tắc Nạp Kho Mail
- `D:\OneDrive\TaadaaData\kibe\gmail_clean_v2.xlsx` là kho mail duy nhất cho cả Gmail và Hotmail.
- **Quy tắc chèn hàng**: TUYỆT ĐỐI CẤM nhét tài khoản mới mua xuống đáy sheet. Nạp cho máy nào phải chèn đúng nhóm hàng của máy đó (sắp xếp tăng dần theo STT Máy 1 -> Máy 80).
- Mailbox có Token Graph API (Hotmail loại 2) bắt buộc 100% đọc mã OTP và Magic Link trên PC qua token dài 457 ký tự. TUYỆT ĐỐI CẤM mở app Outlook trên điện thoại.
- Mail lỗi token / die / không lấy được OTP bắt buộc xóa khỏi `gmail_clean_v2.xlsx` và chuyển sang `D:\Taadaa\Hotmail\hotmail_failed_quarantine.txt` để khiếu nại shop.

## 2. Quy Tắc Cooldown 48 Giờ Khi Dính Rate-Limit TikTok
- Khi TikTok chặn với thông báo: *"Bạn truy cập dịch vụ của chúng tôi quá thường xuyên"* / *"Too many attempts"* / *"Too many requests"*:
  - **CẤM** cố gắng reg lại máy đó ngay lập tức (gây block vĩnh viễn IP/thiết bị).
  - Đánh dấu máy vào `D:\Taadaa\runtime\kibe\device_cooldowns.json` với `cooldown_until = now + 48 hours`.
  - `_detect_clean.py` khi quét target phải tự động bỏ qua (SKIP) các máy đang trong thời gian cooldown (`STT=<N>: COOLDOWN_ACTIVE`).
  - Máy chỉ được nạp/reg lại sau khi đã nghỉ đủ 2 ngày.

## 3. Quy Tắc Xử Lý Lỗi Phân Tầng
- **Lỗi cơ học / UI nhẹ** (timeout nút Tiếp tục màn Tạo pass, picker DOB chậm, OTP cần bấm gửi lại, popup chọn bàn phím Android, popup Cho phép): Agent tự động phân tích ảnh/XML và chạy recovery hoàn tất, không làm phiền user.
- **Lỗi khó / Màn hình lạ**: Chụp ảnh gửi bằng `MEDIA:<đường dẫn>`, giữ nguyên hiện trường màn hình + tạo lock đĩa `device_lock_machine_XX.json` và chờ user chỉ đạo.
