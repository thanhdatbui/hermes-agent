# Google Account Dead Cleanup & Anti-Ban Analysis (2026-08-18)

## 1. Cơ chế xóa tài khoản Google Die khỏi thiết bị và Excel nguồn
Khi tài khoản Gmail vừa tạo bị Google AI gắn cờ checkpoint hậu kiểm (*"Xác minh danh tính của bạn - Vui lòng đăng nhập lại để tiếp tục"*):
1. **Kiểm tra Live Check bằng Core**:
   - Dùng `run_google_live_check` (repo `add mail khoi phuc`) để xác định chính xác trạng thái tài khoản.
   - Nếu dính `Google identity verification / relogin gate`, tài khoản coi như DIE (không thể tự nhận mã OTP do dịch vụ sync bị ngắt).
2. **Quy trình gỡ bỏ khỏi thiết bị**:
   - Gọi hàm `remove_blocked_google_account_from_device(serial, gmail)` từ `add mail khoi phuc/run_add_recovery.py`.
   - Flow: Mở Gmail -> Tap Avatar -> Quản lý các tài khoản trên thiết bị này -> Chọn tài khoản đích -> Bấm "Xóa tài khoản" -> Confirm popup.
3. **Quy trình dọn dẹp Excel nguồn**:
   - Xóa dòng tài khoản tương ứng trong `D:\OneDrive\TaadaaData\kibe\gmail_clean_v2.xlsx`.
   - Lưu ý: Giữ nguyên các tài khoản đã đăng ký TikTok thành công (như Máy 02, Máy 42).

---

## 2. Phân tích nguyên nhân Google AI gắn cờ Checkpoint hàng loạt (Farming Wave Detection)
1. **Jitter tọa độ quá hẹp (Deterministic Touch)**:
   - `_jitter(coord, max_offset=6)`: Điểm chạm chỉ dao động trong bán kính ±4..6 pixel, tạo ra cụm phân bố chạm nhân tạo bất thường so với ngón tay người thật (thường lệch ±12..25px).
2. **Quy luật đặt Username dễ đoán**:
   - Công thức `ho + ten + ddmmyyyy + stt` (ví dụ `quocnga2702200303@gmail.com`) khi tạo liên tục từ cùng 1 ASN/dải IP sẽ bị hệ thống AI của Google gom vào một đợt đăng ký hàng loạt (batch farming wave).
3. **Nhập text bằng ADB thô (`input text`)**:
   - Việc gõ Họ, Tên, Username bằng `input text` bắn cả chuỗi trong vài mili-giây thay vì mô phỏng gõ phím người thật (`human_type` với độ trễ 60–200ms giữa các ký tự).
4. **Thiếu Thinking Delay**:
   - Thời gian chuyển giữa các bước quá nhanh (1.2s–2.5s cố định), thiếu khoảng dừng ngẫu nhiên tự nhiên (3s–6s).

---

## 3. Khắc phục lỗi xoay màn hình (No-Rotation Dual-Layer)
- **Gotcha**: Trên một số dòng Samsung cũ (Galaxy S7 TouchWiz), lệnh `settings put system accelerometer_rotation 0` có thể bị reset về 1 khi WebView Onboarding mở.
- **Giải pháp triệt để**: Bắt buộc ghi cả `settings put` lẫn ghi trực tiếp vào Content Provider:
  - `content insert --uri content://settings/system --bind name:s:accelerometer_rotation --bind value:i:0`
  - `content insert --uri content://settings/system --bind name:s:user_rotation --bind value:i:0`
