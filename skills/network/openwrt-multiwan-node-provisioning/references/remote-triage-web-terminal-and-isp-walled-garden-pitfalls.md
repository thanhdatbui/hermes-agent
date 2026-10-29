# Remote OpenWrt Triage Pitfalls & Protocol

Bài học xương máu từ phiên cứu hộ từ xa Xiaomi R3G V1 qua LuCI ttyd / UltraViewer:

## 1. Remote Clipboard / Web Terminal Command Truncation Trap (UltraViewer / ttyd)
- **Triệu chứng:** Khi copy block lệnh chứa `&&`, `2>&1`, hoặc dán nhiều dòng lệnh một lúc qua UltraViewer vào web terminal (`ttyd` trên LuCI), trình duyệt web tự động nuốt mất ký tự `&` và dấu nối dòng.
  - `cmd1 && cmd2` biến thành `cmd1 cmd2` dẫn đến lỗi `Usage: uci ...`.
  - `2>&1 &` biến thành `2> 1` (ghi ra file `1`) và mất dấu `&` chạy ngầm, làm daemon bị treo foreground hoặc crash khi Ctrl+C.
- **Kỷ luật bắt buộc:**
  - **Mỗi lần chỉ cấp ĐÚNG 1 DÒNG LỆNH ĐƠN LẺ**, tuyệt đối CẤM nối `&&` hay dán block nhiều dòng.
  - Daemon chạy ngầm trên OpenWrt bắt buộc dùng `start-stop-daemon -S -b -x <bin> -- <args>` thay vì dấu `&`.

## 2. Evidence-First Verification Trap: Cấm Tuyệt Đối Bịa Đặt Output / Phán Bừa Không Bằng Chứng
- **Bẫy suy diễn:** Nhìn thấy ping fail hoặc lệnh treo, AI tự động đoán "chắc DNS timeout" hay "wget timeout" rồi giải thích huyên thuyên trong khi màn hình terminal thực tế không hề có dòng đó.
- **Kỷ luật:** Chỉ được khẳng định kết quả dựa trên stdout thực tế đọc được qua OCR/ảnh. Nếu lệnh chưa chạy hoặc chưa có kết quả, phải thừa nhận rõ ràng thay vì phán bừa.

## 3. Interface Naming Case-Sensitivity (Chữ Hoa vs Chữ Thường)
- Trong OpenWrt, interface `WAN2` (viết hoa) sẽ tạo ra device Linux là `pppoe-WAN2`.
- Nếu ping ép interface `ping -I pppoe-wan 8.8.8.8` (chữ thường - interface đang down) thì sẽ rớt 100% packet loss dù `pppoe-WAN2` đang sống khỏe. Luôn kiểm tra `ip -br addr` hoặc `ifstatus <NAME>` để lấy đúng case của `l3_device`.

## 4. Viettel ISP PPPoE Walled Garden / Pool 172.17.x.x Triage
- **Dải 172.17.x.x:** Khi PPPoE nhận IP `172.17.x.x`, ping gateway Viettel (`27.68.227.150`) thông 2ms và nhận cả IPv6 (`2402:800:...`), nhưng ping `8.8.8.8` rớt 100%. Đây là pool cô lập / Walled Garden của ISP (thuê bao mới chưa hoàn công, khóa cước, hoặc chưa gán đúng profile).
- **Phép thử chéo đối chứng (Hardware Cross-Validation):** Thay vì mò mẫm cấu hình router hàng giờ, cắm trực tiếp line mạng vào một thiết bị đang chạy chuẩn (như Box MobiProxy hoặc Router test của kỹ thuật). Nếu cắm vào thiết bị chuẩn mà vẫn nhận 172.17.x / không ra mạng -> chứng minh 100% lỗi từ phía trạm ISP, không tốn thời gian vô ích vào cấu hình router.
