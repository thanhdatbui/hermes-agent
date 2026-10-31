# S7 Farm Proxy Tailscale Isolation & Incident Remediation Runbook (2026-10-31)

## 1. Sự Cố R3G / Tailscale Sập và Farm S7 Bị Kéo Theo (Incident 2026-10-31)
- **Hiện tượng:** Sáng 2026-10-31 (Ca 06:04 và 08:05), 31/79 máy Admin (M201–M280) đồng loạt thất bại trong bước preflight với 2 chữ ký lỗi:
  * 25 máy: `dumpsys connectivity: Wi-Fi not connected`.
  * 6 máy: `egress IP verification failed` (`dial tcp: network is unreachable`).
- **Phân tích cơ chế (Mechanical Failure Chain):**
  1. **Lệch routing Tailscale trên S7:** Toàn bộ dàn Samsung S7 không cài đặt client Tailscale, chỉ kết nối Wi-Fi LAN nội bộ `192.168.110.x`. Ở phiên tối 2026-10-30, file `PROXYgandienthoai.xlsx` bị sửa 32 dòng trỏ sang domain `tb.taadaa.click:5141..5158` (phân giải ra IP Tailscale `100.115.94.49`). Khi S7 cố kết nối qua proxy `100.x.x.x`, kernel Android không có route tới dải CGNAT Tailscale $\rightarrow$ văng lỗi `network is unreachable` hoặc Android Captive Portal check fail $\rightarrow$ tự động ngắt kết nối Wi-Fi.
  2. **R3G OpenWrt sập Tailscale do OOM & Firewall:** Router Xiaomi R3G (128MB RAM) ở xa bị cài đặt 8 tiến trình Tinyproxy đồng thời với nhiều worker con $\rightarrow$ cạn kiệt RAM, Linux OOM Killer tiêu diệt tiến trình `tailscaled`. Đồng thời việc reload firewall OpenWrt khi chưa map zone `tailscale0` chuẩn khiến toàn bộ traffic Tailscale UDP 41641 và SSH 22 bị drop.

## 2. Invariants & Kỷ Luật Hạ Tầng
- **CẤM gán Tailscale IP/Domain cho Phone S7:** TUYỆT ĐỐI CẤM gán domain/IP của mạng Tailscale (`tb.taadaa.click`, `*.taadaa.click` trỏ 100.x, hoặc IP `100.64.0.0/10`) vào `PROXYgandienthoai.xlsx` hay thiết lập proxy của dàn S7. Dàn S7 bắt buộc chỉ được trỏ vào IP LAN nội bộ (`192.168.110.2:10008..10035` trên MikroTik hoặc proxy gateway cục bộ).
- **Cấm đổi file cấu hình khi WAN chưa mở thật:** Tuyệt đối không trỏ proxy máy farm vào node mới (như R3G Thái Bình) khi node đó chưa được test kiểm chứng liveness và egress IP từ bên ngoài.

## 3. Quy Trình Khôi Phục Cấp Tốc (Recovery Runbook O(1))
1. **Khôi phục file Excel nguồn:**
   * Lấy lại bản chuẩn từ `PROXYgandienthoai.xlsx.bak` (các port trỏ về `192.168.110.2:10008..10035`).
   * Đồng bộ sang PC Admin (`192.168.110.119`) qua SSH chunking script (base64) để tránh dính lock OneDrive.
2. **Re-bind Proxy cho toàn bộ dàn S7 qua ADB:**
   * Chạy script ADB hàng loạt trên PC Admin:
     `python D:/Taadaa/AI-Tools/scripts/set_proxy_farm_admin_adb.py`
   * Script sẽ duyệt danh sách máy, gán `settings put global http_proxy 192.168.110.2:<port>` và vô hiệu hóa captive portal detection (`captive_portal_mode 0`).
3. **Nghiệm thu Live với Device Lock:**
   * Dùng `with_device_lock.py --machine <N>` kiểm tra lệnh curl qua `atx-agent` từ chính máy thật:
     `adb.exe -H 192.168.110.119 -s <serial> shell "export http_proxy=http://192.168.110.2:<port>; /data/local/tmp/atx-agent curl --timeout=5s http://ifconfig.me/ip"`
   * Xác nhận trả về IP Public Viettel Đà Nẵng trước khi mở khóa cho batch chạy tiếp.
