# FAILURE EVIDENCE FIRST GATE — ĐÓNG BĂNG HIỆN TRƯỜNG LỖI

## 1. Bản Chất Của Lỗi Gửi Nhầm Ảnh HOME
Khi script tự động (TikTok login, Outlook, Reg, Follow, v.v.) gặp lỗi (OTP sai, sai PIN, Captcha, trắng màn hình WebView SparkActivity, timeout, crash):
- **Flow Sai Cũ**: Bắt Exception/Timeout ➔ Chạy block cleanup/teardown (bấm phím HOME, force-stop app) ➔ Mới chụp ảnh ➔ Gửi ảnh HOME vô nghĩa lên Telegram.
- **Hậu Quả**: Người dùng chỉ thấy màn hình chính của launcher, không thấy được hiện trường lỗi thực tế để kiểm tra và chỉ đạo.

## 2. Quy Tắc Bất Di Bất Dịch (Rule #0 - Freeze Before Anything Else)
Ngay tại millisecond phát hiện lỗi:
1. **NGỪNG NGAY** mọi thao tác ADB di chuyển màn hình (cấm bấm HOME, cấm back, cấm kill app).
2. **CHỤP ĐÓNG BĂNG HIỆN TRƯỜNG NGAY TẠI CHỖ** (`screencap -p`).
3. **VALIDATION**: Kiểm tra `foreground_package` phải là app xảy ra lỗi (TikTok `com.ss.android.ugc.trill`, Outlook, v.v.). CẤM TUYỆT ĐỐI gửi ảnh nếu `foreground_package` là launcher/HOME (trừ trường hợp app bị crash văng hẳn khỏi tiến trình `NO_FOREGROUND_APP_AVAILABLE_AFTER_CRASH`).
4. **GỬI ẢNH QUA TELEGRAM TRƯỚC** (`MEDIA:<đường dẫn tuyệt đối>`).
5. **CHỈ SAU KHI ĐÃ GỬI BẰNG CHỨNG XONG** mới được phép chạy lệnh cleanup / teardown về HOME.

## 3. Template Bắt Buộc Khi Báo Cáo Lỗi
```text
MEDIA:D:\Taadaa\runtime\failure_evidence\freeze_m<May>_<acc>_<Stage>_<Timestamp>.png
### [MÁY XX] - <Nhóm Lỗi / Tên Màn Hình Bị Kẹt>
- Stage: <OTP_VERIFY / PIN_INPUT / CAPTCHA / WEBVIEW_WHITE>
- Trạng thái màn hình: FROZEN (đang giữ nguyên hiện trường app)
- Chi tiết lỗi: <Thông báo lỗi UI / Logcat / Mã PIN không khớp>
- Hành động đề xuất / bước tiếp theo: <...>
```
