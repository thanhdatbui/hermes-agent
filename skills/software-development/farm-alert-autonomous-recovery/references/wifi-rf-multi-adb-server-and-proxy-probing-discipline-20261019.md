# Kỷ Luật Chẩn Đoán Wi-Fi, Khảo Sát Băng Tần & Cơ Chế Đa ADB Server

## 1. Cơ Chế Đa Daemon ADB Server Trên Windows Host (Port 5037 vs 5038)
- **Hiện tượng:** Chạy `adb devices` trên CLI mặc định báo thiếu máy, `device not found`, hoặc mất kết nối với một số thiết bị (như M7).
- **Nguyên nhân gốc rễ:**
  * Host farm chạy đồng thời tiến trình điều khiển màn hình **XiaoWei** (`adb.exe` tại `C:\Program Files (x86)\xiaowei\tools\adb.exe` chiếm port mặc định `5037`).
  * Hệ thống farm hoặc daemon nền thứ hai chạy trên **Port 5038** (PID `10084`).
  * Một số thiết bị Android (như M7, M18, M30) được gán kết nối riêng vào daemon port `5038`.
- **Kỷ luật xử lý:**
  * **CẤM TUYỆT ĐỐI phán ẩu "máy bị rút cáp/rút nguồn"**: Trước khi kết luận máy offline phần cứng, BẮT BUỘC kiểm tra PnP của Windows:
    `powershell.exe -NoProfile -Command "Get-PnpDevice -PresentOnly | Where-Object { $_.InstanceId -like '*<SERIAL>*' }"`
  * **Truy vấn qua socket port 5038**:
    Thiết lập biến môi trường `ADB_SERVER_SOCKET=tcp:127.0.0.1:5038` hoặc dùng socket protocol trực tiếp (`host:transport:<serial>` -> `shell:<cmd>`) để giao tiếp với máy mà không làm gián đoạn XiaoWei.

## 2. Kỷ Luật Khảo Sát Mạng Wi-Fi & RF Management
- **Quy hoạch 40 máy/AP:**
  * Mốc 40 máy/AP là **khuyến nghị cân bằng tải RF** để đảm bảo airtime khi đồng loạt lướt video, **KHÔNG PHẢI trần cứng kỹ thuật** của Aruba Instant AP (ngưỡng `Max Clients Threshold` cấu hình là 64).
  * CẤM Coordinator viện cớ "trần cứng 40 máy" để từ chối điều phối hay suy diễn sai lệch.
- **Hiện tượng lệch băng tần & Phản xạ RF (5 GHz vs 2.4 GHz):**
  * Sóng 5 GHz (bước sóng ngắn ~6cm) rất nhạy cảm với vật cản kim loại và góc kệ sắt hộp (RF Shadowing).
  * Kiểm tra độ nhạy thu phát giữa các kênh 5 GHz: Kênh thấp (UNII-1, ch 36-48) công suất phát thường thấp hơn các kênh cao (UNII-2C/3, ch 100-149).
  * **CẤM tùy tiện mở băng tần 2.4 GHz (`Band: all`) trên SSID farm:** 2.4 GHz băng thông hẹp (20MHz), nếu mở sẽ gây hiện tượng "Sticky Client" kéo tụt 10-20 máy khác xuống 2.4 GHz, làm bão hòa airtime và rớt proxy diện rộng.
- **Cấm suy diễn thiết bị từ tiền tố MAC OUI:**
  * CẤM tra cứu tiền tố OUI rồi tự ý gán ghép thương hiệu lạ ngoài farm (như gán MAC gateway `192.168.110.1` thành "router Xiaomi" khi farm không sử dụng). BẮT BUỘC tôn trọng cấu trúc mạng của User.

## 3. Kiểm Tra Proxy Bằng Shell Trên Android 8 / Samsung S7
- Thiết bị Samsung S7 (Android 8) KHÔNG có sẵn binary `curl` hay `nc` chuẩn.
- Lệnh kiểm tra proxy từ shell thiết bị:
  * Dùng `toybox nc -w 3 <proxy_ip> <proxy_port>`.
  * Gửi request HTTP CONNECT:
    `echo -e "CONNECT httpbin.org:80 HTTP/1.1\r\nHost: httpbin.org:80\r\n\r\n" | toybox nc -w 3 192.168.110.2 20007`
  * Nhận `HTTP/1.1 200 Connection established` xác nhận thông suốt 100%. CẤM gọi `curl` rồi thấy rỗng suy diễn đứt mạng.

## 4. Kỷ Luật Ứng Xử Điều Phối: Cấm Khóc Lóc Đùn Đẩy Việc Bấm Tay
- Khi gặp khó khăn trong kết nối mạng hay thao tác UI: **CẤM TUYỆT ĐỐI khóc lóc yêu cầu User bấm tay qua màn hình**.
- Nhiệm vụ của Coordinator là sử dụng tự động hóa (ADB socket qua đúng port, nạp Intent `com.steinwurf.adbjoinwifi`, hoặc API Aruba) để giải quyết dứt điểm vấn đề trong quyền hạn đã được cấp.
