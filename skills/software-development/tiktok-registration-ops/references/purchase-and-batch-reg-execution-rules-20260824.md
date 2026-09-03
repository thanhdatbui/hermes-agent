# Quy Trình Mua Hotmail & Chạy Batch Reg TikTok Đồng Loạt (2026-08-24)

## 1. Mua Hotmail & Pre-Validation Token
- **API Mua**: BoxTaiKhoan (`id: 60` - Hotmail OAuth2).
- **Test Token**: Bắt buộc kiểm tra 100% Refresh Token qua Microsoft Graph OAuth2 endpoint (`login.microsoftonline.com/consumers/oauth2/v2.0/token`) trước khi nạp sheet.
- **Nạp CSDL**: Thêm các dòng hợp lệ vào `gmail_clean_v2.xlsx` (Cột 1: STT, Cột 2: Email, Cột 3: Pass, Cột 7: Ngày nạp, Cột 9: Token, Cột 10: Client ID).

## 2. Tiêu Chuẩn Thực Thi Trọn Gói & Không Chạy Đơn Lẻ
- Khi user yêu cầu "mua mail reg tiktok": Làm liền mạch trọn gói từ mua ➔ test token ➔ nạp sheet ➔ khởi chạy batch reg đồng loạt. Tuyệt đối không dừng lại ở bước mua tài khoản.
- Luôn chạy đồng loạt (`_run_all_targets.py` hoặc batch runner với `DEVICE_LOCK_ENABLED=1`), không bao giờ chạy lẻ tẻ từng máy đơn lẻ trừ khi user chỉ định đúng 1 máy.

## 3. Live Proxy IP Preflight Gate
- Trước khi khởi chạy, bắt buộc verify live IP qua broadcast:
  `am broadcast -a vn.vichanger.app.GET_IP -n vn.vichanger.app/.AdbCaller`
- Điều kiện PASS: `result=200` và `IP != 1.53.114.53` (khác Direct IP farm).
- Bỏ qua các máy timeout / lỗi proxy (ví dụ STT 36, 62, 63, 75) qua `TIKTOK_REG_SKIP_STTS`.

## 4. Bảo Vệ Hiện Trường Lỗi & Device Lock
- Khi máy gặp lỗi trong quá trình reg: Giữ nguyên `device lock` và giữ nguyên màn hình hiện trường app.
- CẤM tuyệt đối tự ý chạy lệnh cleanup hàng loạt (`force-stop`, `KEYCODE_HOME`) làm mất màn hình lỗi trước khi user kiểm tra.
- Chụp screencap gửi ảnh thật qua Telegram (`MEDIA:<path>`) để user hướng dẫn xử lý.
