# Farm Proxy Quarantine & Multi-Cluster Batch Isolation Protocol

## 1. Bối Cảnh Sự Cố & Tử Huyệt Dồn Chung 1 IP Egress (Collapse to Single IP)
Khi router phụ trách xoay nhiều đường mạng PPPoE (như OpenWrt Xiaomi R3G) gặp sự cố:
- Tinyproxy bị comment out dòng `#Bind $ip_addr` hoặc cấu hình routing đa đường bị rớt về Default Gateway.
- Tất cả các port proxy (ví dụ 5141..5158) dù đang mở port và phản hồi `200 OK` nhưng khi ra ngoài Internet đều bị trỏ ra chung **ĐÚNG 1 IP PUBLIC DUY NHẤT** (ví dụ dải CGNAT `100.77.x.x` NAT ra `117.5.152.203`).
- **Điểm mù Preflight đơn lẻ (Single-Device Preflight Blind Spot):** Nếu máy chỉ test đơn lẻ xem có ra được Internet hay không, từng máy đều báo `PASS` vì vẫn cào được IP. Nhưng khi chạy đồng loạt 32 máy vào ca nuôi TikTok, hàng chục acc sẽ bị dính chùm cùng 1 IP $\rightarrow$ Ăn gậy shadowban / cấm chùm tài khoản!

## 2. Quy Trình Cách Ly Khẩn Cấp 4 Tầng (4-Tier Quarantine Invariant)
Trước khi sự cố định tuyến đa đường trên router/proxy được giải quyết dứt điểm, Coordinator BẮT BUỘC thực hiện quy trình cách ly 4 tầng lập tức để phiên nuôi acc kế tiếp không tự động nạp các máy lỗi:

### Tầng 1: Đánh dấu Cách Ly trong Sổ Excel SSOT (`PROXYgandienthoai.xlsx`)
- Ghi đè cột `Proxy` của toàn bộ danh sách máy dính lỗi thành:
  `QUARANTINE_R3G_INVESTIGATION` (hoặc `QUARANTINE_PROXY_ERROR`).
- Đẩy ngay file Excel chuẩn sang các máy trạm vận hành (Admin-PC qua `push_proxy_excel_to_admin.py`).

### Tầng 2: Cập nhật Master Database SQLite (`farm_master.db`)
- Đồng bộ bảng `machines`:
  ```sql
  UPDATE machines SET proxy_endpoint='QUARANTINE_R3G_INVESTIGATION' WHERE owner='admin' AND machine_id IN (<danh_sach_may>);
  ```
- Mọi DAL/API truy vấn gán proxy tự động sẽ nhận diện máy đang trong diện cách ly và từ chối cấp proxy.

### Tầng 3: Khử trùng lặp và loại trừ khỏi Lịch Chạy An Toàn (`taikhoan_run_safe.xlsx`)
- Kiểm tra danh sách tài khoản hợp lệ trong `taikhoan_run_safe.xlsx`.
- Loại bỏ hoàn toàn các dòng thuộc về những máy đang cách ly. Chỉ giữ lại các máy kênh chính có proxy riêng biệt đã được kiểm chứng độc lập.

### Tầng 4: Cắt Proxy trực tiếp trên phần cứng Android (Hardware Kill-Switch)
- Gửi lệnh qua ADB gỡ bỏ hoàn toàn proxy trên máy:
  ```bash
  adb -s <SERIAL> shell settings put global http_proxy :0
  ```
- Kiểm chứng read-back: `settings get global http_proxy` trả về `:0`.
- Khi máy không có proxy, cơ chế Preflight (`preflight.py`) khi khởi động ca nuôi sẽ bắt buộc báo lỗi `Wi-Fi not connected` / `Egress IP verification failed` và **FAIL-CLOSED DỪNG LẬP TỨC**, tuyệt đối không bật app TikTok hay switch profile.

## 3. Kỷ Luật Báo Cáo: Cấm "Báo Cáo Cổng Live Lấp Liếm" (Anti-False-Positive Reporting)
- **CẤM TUYỆT ĐỐI:** Thấy các cổng proxy `OPEN` hoặc trả về `HTTP 200` là vội vã báo cáo "hệ thống đã LIVE / hoàn tất".
- **BẮT BUỘC ĐỐI SOÁT COLLISION:** Phải gom nhóm các IP Egress trả về từ từng cổng proxy. Nếu phát hiện $> 2$ máy / $> 1$ cổng proxy ra chung 1 địa chỉ IP công cộng (trừ cụm đã được phê duyệt), BẮT BUỘC coi đó là **SỰ CỐ NGHIÊM TRỌNG (ROUTING COLLISION)** và tiếp tục điều tra, cấm nghiệm thu!
