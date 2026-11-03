# Quy Chuẩn Điều Hành Giao Diện Proxy Farm (Mẫu Chuẩn MobiProxy test.taadaa.click)

## 1. Bản Sắc & Triết Lý Thiết Kế MobiProxy
Mẫu giao diện MobiProxy (`test.taadaa.click`) là tiêu chuẩn hiển thị tối cao cho toàn bộ hạ tầng proxy của farm (cả R3G Thái Bình và MikroTik Đà Nẵng). Mọi giao diện bảng điều khiển proxy bắt buộc phải tuân thủ nghiêm ngặt các quy tắc sau:

### Cấu Trúc Bảng 8 Cột Chuẩn:
1. **PROXY / TÊN INTERFACE:** Mã định danh duy nhất (`R3G-5141`, `pppoe-out1`).
2. **NGUỒN:** Nguồn line vật lý (`R3G`, `Lan1`, `PPPoE`).
3. **IPV4 / IPV6 (IP PUBLIC):** Địa chỉ IP WAN Internet thực tế do nhà mạng cấp (font monospace, có nút copy). Tuyệt đối CẤM hiển thị dấu `—` đối phó khi chưa probe thực tế.
4. **CỔNG:** Cổng client kết nối vào (`5141`, `10001`).
5. **UPTIME (TIME LIVE):** Thời gian sống thực tế của IP/line tính theo câu chữ tiếng Việt tự nhiên (`55 phút`, `20 giờ 17 phút`, `1 ngày 14 giờ`). Tuyệt đối KHÔNG hiển thị định dạng thô `00:26:13` hay giây nguyên bản.
6. **TRẠNG THÁI:** Badge màu sắc trực quan (`🟢 LIVE` cho online, `🔴 OFFLINE` hoặc `🟡 DOWN` cho lỗi).
7. **HẸN GIỜ (PHÚT):** Ô input số (`type="number" min="1" max="1440"`) riêng biệt trên từng hàng cho phép đặt lịch reset tự động từng cổng độc lập.
8. **RESET / THAO TÁC:** Nút bấm `↻ Reset` hoặc `🔄 Đổi IP` kích hoạt đổi IP tức thời, không hiển thị confirm popup làm phiền người vận hành.

---

## 2. Thanh Công Cụ Hẹn Giờ (Schedule Toolbar)
Phía trên bảng danh sách proxy bắt buộc phải có thanh công cụ điều khiển hàng loạt:
- **Ô nhập phút toàn cục (`Số phút`):** Cho phép nhập số phút nhanh.
- **Nút `Áp dụng tất cả`:** Gán nhanh số phút vừa nhập cho toàn bộ danh sách các cổng.
- **Nút `💾 Lưu lịch reset`:** Lưu toàn bộ cấu hình vào file JSON backend (`r3g_schedules.json` hoặc `schedules.json`) và kích hoạt daemon thread tự động đổi IP định kỳ.
- **Nút `↻ Reset tất cả N port`:** Gửi yêu cầu đổi IP đồng loạt cho toàn bộ các cổng chỉ với 1 click.

---

## 3. Tối Ưu Mobile Responsive
- Bao bọc bảng bằng container `.r3g-table-wrap` có `-webkit-overflow-scrolling: touch;` và `overflow-x: auto;`.
- Bảng trên màn hình nhỏ cho phép vuốt ngang mượt mà, padding nhỏ gọn `10px 8px` với cỡ chữ `13px`.
