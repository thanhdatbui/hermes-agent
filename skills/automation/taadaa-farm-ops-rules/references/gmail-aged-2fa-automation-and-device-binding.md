# Quy chuẩn Tự động hóa Bật 2FA cho Gmail Ngâm 24-48h & Silent Watchdog

## 1. Bối cảnh & Mục tiêu
- Sau khi đăng ký hoặc nạp tài khoản Gmail vào thiết bị Samsung (GemPhoneFarm), tài khoản cần được ngâm 24h - 48h để vượt qua giai đoạn nhạy cảm ban đầu của Google.
- Sau Ca 1 (nuôi feed buổi sáng), các máy rơi vào trạng thái rảnh rỗi. Đây là thời điểm vàng để watchdog kích hoạt quy trình bật 2-Step Verification (2FA Google Authenticator) on-device cho Gmail.

## 2. Nguyên tắc Silent Watchdog (no_agent = True)
1. **Zero-Item Silent:**
   - Nếu trong khung giờ kiểm tra nhưng:
     - Chưa hoàn thành Ca 1
     - Hoặc có feed runner đang chạy / dính device-lock
     - Hoặc không có ứng viên (candidate) nào đủ tuổi ngâm (days >= 1) và chưa có 2FA
     - Hoặc tất cả máy ứng viên đều bận / offline
   - Script BẮT BUỘC thoát êm (`sys.exit(0)`) mà KHÔNG in bất kỳ ký tự nào ra `sys.stdout`.
2. **Stdout là Kênh Delivery Duy Nhất:**
   - Hermes Cron Scheduler bắt toàn bộ nội dung in ra `stdout` để gửi qua Telegram channel cấu hình trong `deliver: telegram:...`.
   - TUYỆT ĐỐI KHÔNG in template báo cáo rỗng dạng `Tổng máy đủ điều kiện: 0`, `Success: []`, `Fail: []` ra stdout vì sẽ gây spam nhóm liên tục mỗi chu kỳ cron (5-10 phút).
   - Toàn bộ log trung gian, cảnh báo, thông tin kiểm tra bắt buộc ghi ra `sys.stderr` hoặc file log.

## 3. Quy chuẩn Dữ liệu & Mapping Thiết bị
- **Mapping Thiết bị:**
  - Không scan mù thiết bị ADB rồi gán ngẫu nhiên tài khoản.
  - Phải đọc ánh xạ số thứ tự máy `stt` ↔ `serial` từ `D:\OneDrive\TaadaaData\kibe\PROXYgandienthoai.xlsx`.
- **Dữ liệu Ứng viên (Candidates):**
  - Đọc từ `D:\OneDrive\TaadaaData\kibe\gmail_clean_v2.xlsx`.
  - Cột 0: STT (số máy tương ứng).
  - Cột 1: Email (phải kết thúc bằng `@gmail.com`).
  - Cột 3: Secret 2FA (nếu rỗng / None / null là chưa bật 2FA).
  - Cột 6: Ngày tạo (`created_at`). Tính tuổi ngâm: `days_ago = (today - created_date).days >= 1`.
- **Thư viện Thực thi:**
  - Import hàm nghiệp vụ `enable_2fa_device(serial, email)` từ `D:\Taadaa\tools\enable_gmail_2fa_device.py`.
  - Sử dụng ADB binary chuẩn: `C:\Users\Kibe\.GemPhoneFarm\app\adb-tool\adb.exe`.

## 4. 3 Tầng Bảo vệ Xung đột Cron
Trước khi gửi lệnh bật 2FA tới thiết bị, bắt buộc qua 3 cổng kiểm tra:
1. **Lịch Nuôi Acc (TikTok Feed Manifest):** Máy không nằm trong slot đang chạy hoặc cách slot kế tiếp >= 60 phút.
2. **Device Lock Vật lý:** Máy không dính file lock nào trong `C:\Users\Kibe\AppData\Local\automation-core\device-locks` (`active`, `running`, `queued`, `blocked`).
3. **Lock-Aware Isolation:** Thiết bị phải online trên ADB trước khi tiến hành thao tác.
