# GPM Chromium Core Mismatch, 64-bit Conversion & Proxy Format Pitfalls

## 1. Lỗi "Yêu cầu cập trình duyệt [Chromium] [XXX]"
### Triệu chứng
- Khi gọi API start profile `GET /api/v3/profiles/start/{id}` hoặc bấm "Mở" trên UI:
  `{"success": false, "data": null, "message": "Yêu cầu cập trình duyệt [Chromium] [142]"}` (hoặc version khác như `[127]`, `[137]`).
- Thư mục binary trình duyệt `gpm_browser/gpm_browser_chromium_core_XXX` thực tế **ĐÃ CÓ TRÊN ĐĨA** và chạy trực tiếp bình thường.

### Nguyên nhân gốc rễ
1. **Kiến trúc nhị phân 32-bit vs 64-bit (`ConvertProfileTo64bit`):**
   - Các gói core Chromium hiện đại (từ v137 trở lên) thường là bản dựng **64-bit (x64)**.
   - Profile tạo mới mặc định có thể bị cấu hình cờ 32-bit (`ConvertProfileTo64bit: false`).
   - GPM v4.3.6+ kiểm tra tính tương thích giữa profile architecture và binary core. Nếu lệch, API start profile sẽ chặn và báo lỗi giả lập "Yêu cầu cập trình duyệt".
2. **Khóa chức năng do modal "Big Update":**
   - Khi app GPMLogin mở lên và có dialog modal thông báo (ví dụ cập nhật Fingerprint database), giao diện bị block dạng modal. Các lệnh khởi động profile qua API v3 có thể bị quăng lỗi tương tự.

### Cách xử lý
- **Trên UI GPMLogin:**
  - Chọn nhóm profile cần chạy -> Chọn menu **Chuyển profile sang 64bit** (hoặc trong tính năng Quản lý Profile).
  - Khuyến nghị: Chọn chuyển theo từng nhóm nhỏ, không nên chọn "All" để tránh làm thay đổi fingerprint của các profile cũ đang sống ổn định.
- **Trong SQLite DB:**
  - Cập nhật trường `ConvertProfileTo64bit = true` trong `JsonData` của bảng `Profiles` nếu profile dùng core Chromium 64-bit.

---

## 2. Lỗi Cột Proxy hiển thị "http:0" trên bảng GPMLogin
### Triệu chứng
- Cột Proxy trên UI GPM hiển thị `http:0` thay vì hiển thị địa chỉ proxy chuẩn (dù dữ liệu proxy đã được gán).

### Nguyên nhân
- Khi tạo hoặc cập nhật profile, nếu gán `raw_proxy` dạng chuỗi có chứa scheme `http://` kèm chú thích trong ngoặc đơn:
  `http://192.168.110.2:20061 (test.taadaa.click:5127)`
- Bộ parser hiển thị UI của GPM v4 không parse được chuỗi có dấu ngoặc đơn và tiền tố `http://`, dẫn đến nhận diện sai port thành `0`.

### Chuẩn hóa Proxy định dạng GPM
- Luôn truyền đúng format chuẩn của GPM API:
  - MobiProxy 4G: `test.taadaa.click:51XX:mobiXX:TaadaaMobi#2026!`
  - MikroTik: `mirotik1.taadaa.click:1000X:admin@1:admin@1`
- Tuyệt đối không chèn thêm chú thích text `(...)` vào trường `raw_proxy`. Nếu cần lưu thông tin phụ, lưu vào trường `note`.
