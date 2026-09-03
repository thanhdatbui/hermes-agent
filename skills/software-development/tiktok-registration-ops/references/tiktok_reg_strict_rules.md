# TikTok Reg Operations & Reporting Rules

## 1. Quy tắc Lock thiết bị
- CHỈ nhả lock đối với máy chạy **SUCCESS** (đã verified và ghi tracking đầy đủ).
- Máy **FAILED / LỖI / DỪNG GIỮA CHỪNG:** Bắt buộc **GIỮ NGUYÊN LOCK `blocked`**, tuyệt đối không được nhả lock để bảo vệ hiện trường.

## 2. Quy tắc ghi Password Excel (Workbook)
- Nếu đăng ký không qua màn nhập mật khẩu (flow OTP / email-only): Cột **PASS** trong file Excel tracking (`taikhoan_dat_v2_updated .xlsx`) **BẮT BUỘC ĐỂ TRỐNG (`None`)** để sau này vào TikTok cài pass thủ công.
- **CẤM** tự ý sinh pass ngẫu nhiên lưu vào khi không qua màn nhập password.

## 3. Quy tắc gửi ảnh hiện trường & Báo cáo
- Khi máy lỗi / dừng phiên: Bắt buộc chụp ảnh kèm **BANNER ĐỎ** trên đầu ảnh: `[MAY XX] - HH:MM DD/MM` (dùng overlay banner tương tự `automation_core.alerts.send_farm_machine_alert`).
- Báo cáo hoàn toàn bằng **tiếng Việt ngắn gọn, súc tích**, giải thích rõ nguyên nhân; **CẤM** giải thích bằng khối log/thuật ngữ tiếng Anh dông dài.

## 4. Quy tắc Check Live Gmail (khi không nhận được OTP)
- Khi Gmail không nhận được OTP mới, kiểm tra trạng thái live của tài khoản Google: Vào Gmail -> Avatar -> bấm nút **"Quản lý Tài khoản Google của bạn"**.
- Nếu màn hình báo *"Hoàn tất đăng nhập để tiếp tục / Đã xảy ra lỗi và bạn cần đăng nhập lại"* -> Tài khoản bị văng session (Session Expired/Relogin Required), không thể nhận mail OTP mới.
