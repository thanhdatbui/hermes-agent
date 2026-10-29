# GPM Profile Proxy Safety Invariant & Post-Reboot Resource Sync Protocol

## 1. Cấm Tuyệt Đối Chạy Profile Farm Không Có Proxy (Direct IP Leak Ban)
- **Căn nguyên sự cố:** Khi thực hiện tác vụ tự động hóa hoặc đăng ký dịch vụ (như AWS / Gmail / Hotmail / TikTok), việc tự ý tạo profile GPM mới không gắn proxy (`raw_proxy == ""`) hoặc chọn profile farm nhưng không xác thực proxy làm rò rỉ IP trực tiếp của máy host (Kibe/Admin).
- **Hậu quả:** Khiến toàn bộ dàn tài khoản nuôi bị liên đới (chain ban), cờ bot Google / AWS kích hoạt và làm hỏng tài sản farm.
- **Quy tắc bất biến:**
  1. Mọi profile GPM liên quan đến farm (Gmail, Hotmail, TikTok) BẮT BUỘC phải mang proxy di động (MobiProxy / MikroTik) hợp lệ.
  2. Trước khi khởi động profile: BẮT BUỘC kiểm tra trường `raw_proxy` qua API `GET /api/v3/profiles/{id}`. Nếu `raw_proxy` rỗng hoặc bị xóa -> DỪNG NGAY (FAIL-CLOSED), cấm mở trình duyệt.
  3. Sau khi khởi động Chromium qua CDP: BẮT BUỘC điều hướng đến `https://api.ipify.org?format=json` để đọc IP thực tế và so khớp với dải IP proxy được giao trước khi điều hướng sang trang đích.

## 2. Xử Lý Hiện Tượng GPM Đòi Cập Nhật Resource Sau Reboot Máy
- **Hiện tượng:** Sau khi máy reboot (như chu kỳ 05:20 sáng), khi gọi API khởi động profile v3, GPM trả về lỗi:
  ```json
  {"success": false, "data": null, "message": "Yêu cầu cập trình duyệt [Chromium] [142]"}
  ```
- **Bản chất kỹ thuật:**
  - File thực thi và DLL trong `gpm_browser_chromium_core_142` trên đĩa vẫn nguyên vẹn 100%.
  - Khi app GPMLogin khởi động mới sau reboot, logic nội bộ yêu cầu đồng bộ trạng thái runtime/manifest với server GPMLogin trước khi Local API v3 cho phép khởi chạy profile.
- **Quy trình kích hoạt:**
  - Không tự tiện xóa hay ghi đè lung tung vào thư mục core trình duyệt.
  - Khởi chạy app GPM với cửa sổ hiển thị, thực hiện thao tác mở profile trên app hoặc xác nhận cập nhật gói tài nguyên qua giao diện GPM để hệ thống nạp lại manifest hợp lệ.
