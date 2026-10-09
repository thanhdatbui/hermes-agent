# Bẫy Lệch Giờ Hệ Thống Samsung S7 (Năm 2016) Gây Lỗi SSL & Fake "Không Có Internet" (12/09/2026)

## 1. Hiện Tượng Nghịch Lý
- Máy Samsung S7 kết nối Wi-Fi nhận IP LAN bình thường (`192.168.110.x`), ping router `192.168.110.2` 0% packet loss (~9ms).
- Gán proxy qua ADB `settings put global http_proxy 192.168.110.2:200xx` thành công.
- Trình duyệt truy cập plain HTTP (như `http://api.ipify.org`) vẫn hiển thị đúng Public IP của proxy.
- **NHƯNG:**
  - Status bar Wi-Fi hiện `content-desc="Tín hiệu Wi-Fi đủ., Không có Internet."`.
  - `dumpsys connectivity` báo `Score{20}`, `lastValidated{false}`, `everValidated{false}`.
  - Mở app TikTok thì văng ngay toast: *"Không có kết nối Internet. Vui lòng kết nối với Internet và thử lại"* và kẹt lớp phủ *"Đã xảy ra lỗi / Thử lại sau"* (nút `dcj`).

## 2. Nguyên Nhân Gốc Rễ
1. **Mất nguồn/Reboot làm tụt RTC:** Khi điện thoại Samsung S7 mất nguồn pin hoặc bị reboot cứng, đồng hồ thời gian thực (RTC) bị reset về mốc xuất xưởng kernel (ví dụ: `Sat Jan 2 14:49:33 2016`).
2. **`auto_time` bị tắt (`0`):** Do cấu hình máy vô tình tắt cập nhật giờ mạng (`settings get global auto_time` trả về `0`), máy không tự đồng bộ lại giờ qua giao thức NTP sau khi khởi động.
3. **Từ chối chứng chỉ TLS/SSL (Certificate Not Yet Valid):**
   - Mọi chứng chỉ SSL/TLS của máy chủ TikTok (`*.tiktok.com`, `*.tiktokv.com`) và Google được cấp phát trong giai đoạn 2024–2026.
   - Khi thiết bị đứng ở mốc năm **2016**, Android SSL engine phát hiện thời gian hiện tại nằm **TRƯỚC** thời điểm bắt đầu có hiệu lực (`NotBefore`) của chứng chỉ.
   - Toàn bộ kết nối HTTPS bị ngắt ngay tại bước TLS Handshake (`SSLHandshakeException: Certificate not yet valid`).
   - TikTok dùng engine mạng TTNet/Cronet kiểm tra TLS fail nên lập tức kết luận thiết bị không có mạng Internet.

## 3. Quy Trình Kiểm Tra & Khắc Phục O(1)

### Bước 1: Kiểm tra đồng hồ thiết bị
```bash
adb -s <serial> shell date
```
Nếu thấy năm hiển thị là `2016` (hoặc lệch khác năm 2026):

### Bước 2: Bật lại tự động đồng bộ giờ qua mạng
```bash
adb -s <serial> shell "settings put global auto_time 1 && settings put global auto_time_zone 1"
```
Đồng hồ sẽ lập tức đồng bộ về đúng năm 2026 sau 1–2 giây.

### Bước 3: Xác minh hồi phục
```bash
adb -s <serial> shell date
# Kết quả: Sat Sep 12 14:xx:xx +07 2026

adb -s <serial> shell "dumpsys connectivity | grep -E 'VALIDATED|everValidated'"
# Kết quả: Capabilities: ... &VALIDATED& ... Score{60} everValidated{true} lastValidated{true}
```
Mở lại app TikTok: SSL Handshake thông suốt, bảng tin For You (Đề xuất) load video và hiển thị bình thường.
