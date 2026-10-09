# Pitfall & Quy trình xử lý lỗi "Yêu cầu cập trình duyệt [Chromium] [XYZ]" trên GPMLogin

## 1. Bản chất của lỗi
Khi gọi API `/api/v3/profiles/start/{id}` và nhận response:
```json
{"success": false, "data": null, "message": "Yêu cầu cập trình duyệt [Chromium] [142]"}
```
Dù trong thư mục `gpm_browser/gpm_browser_chromium_core_142` **đã có sẵn binary** và profile đã được tạo trước đó:

### Có 2 nguyên nhân chính:
1. **Modal Dialog "Big Update" hoặc Thông báo mới chặn UI app GPM:**
   - App GPMLogin v4.3.x khi khởi động có thể bật modal popup "Big Update" (thông báo cập nhật fingerprint mới, phiên bản Global...).
   - Khi modal này hiển thị, backend engine của GPMLogin tạm block tương tác mở profile và giả lập trả lỗi này qua API.
   - *Cách kiểm tra:* Chụp màn hình cửa sổ GPMLogin (`PrintWindow` qua Win32 API). Nếu thấy popup che mờ màn hình, đóng popup.
2. **Server GPM nâng cấp Fingerprint Database hoặc ép update patch core browser:**
   - Khi GPM phát hành DB fingerprint mới (ví dụ 411), các profile Chromium cũ (ví dụ `142.0.7444.163` version 1.0) bị server GPM gắn cờ outdated.
   - Khi đó, dù modal thông báo đã tắt hoàn toàn, API vẫn trả về `Yêu cầu cập trình duyệt [Chromium] [142]` cho đến khi core được cập nhật.

## 2. Quy trình xử lý triệt để

### A. Kiểm tra UI hiện trường GPM
Chụp ảnh cửa sổ GPMLogin bằng lệnh Win32 `PrintWindow` để xác định trạng thái UI:
- Nếu popup "Big Update" đang hiện:
  - Nếu GPM chạy cùng privilege level (standard): Có thể dùng Windows API gửi `WM_LBUTTONDOWN`/`UP` hoặc `mouse_event` vào nút "Đóng thông báo" (tọa độ ~ giữa ngang `w/2`, dọc `h * 0.772`).
  - Nếu GPM chạy Elevated/Admin còn agent chạy Standard: Windows UIPI sẽ chặn pointer synthetic. Cần thông báo User click nút đóng trên màn hình, hoặc chạy lại agent/GPM đồng cấp quyền.

### B. Cập nhật Core trình duyệt trong GPM (Khi đã tắt popup mà API vẫn chặn)
- Trên giao diện GPMLogin:
  1. Click icon **Cài đặt (Bánh răng)** ở thanh sidebar menu dọc bên trái (icon thứ 6 từ trên xuống).
  2. Chọn tab **Trình duyệt (Browser)**.
  3. Tìm dòng phiên bản cần chạy (ví dụ **Chromium 142**) rồi click nút **Tải về / Cập nhật**.
  4. Đợi tiến trình tải và giải nén hoàn tất 100%.
- Sau khi cập nhật xong, gọi lại API `/api/v3/profiles/start/{id}` sẽ trả về `success: true` ngay lập tức.

## 3. Quy tắc báo cáo Watchdog (Ngắn gọn - Action-First)
- Khi phát hiện lỗi hàng loạt profile bị chặn do core Chromium:
  - **Không** spam log chi tiết từng profile gây loãng tin nhắn Telegram.
  - Tóm tắt 1 dòng trạng thái: `[POOL HEALER] ChatGPT-Web: X/Y | Antigravity: A/B | Cần xử lý: N acc (GPM Chromium outdated: K, Thiếu profile: M)`.
  - Chỉ rõ hành động cần làm: Vào Cài đặt GPM -> Trình duyệt -> Bấm Cập nhật Chromium core tương ứng.
