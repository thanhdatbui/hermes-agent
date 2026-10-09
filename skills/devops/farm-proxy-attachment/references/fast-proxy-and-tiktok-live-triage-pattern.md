# Quy Trình Triage Kiểm Tra Nhanh Proxy Khi User Nghi Ngờ Lỗi Mạng (O(1))

## Bối Cảnh
Khi user hỏi ngắn gọn: *"Kiểm tra có lỗi proxy k v"*, tránh suy diễn lý thuyết hoặc trả lời chung chung. Cần thực hiện kiểm tra đa tầng từ ngoài vào trong và phản hồi trực diện.

## Các Bước Kiểm Tra O(1) Bắt Buộc

### 1. Host Probe (Từ máy tính Kibe)
- Đọc port proxy của máy qua: `adb shell settings get global http_proxy` (hoặc tra cứu Singbox mapping: `D:\Taadaa\AI-Tools\config\singbox_config.json` ➔ `20000+N`).
- Kiểm tra 4 endpoint qua proxy `192.168.110.2:<PORT>`:
  * `http://api.ipify.org` (HTTP plain) ➔ Status 200, IP trả về đúng dải Viettel.
  * `https://api.ipify.org` (HTTPS SSL handshake) ➔ Status 200.
  * `http://connectivitycheck.gstatic.com/generate_204` ➔ Status 204 No Content.
  * `https://www.tiktok.com` ➔ Status 200 OK.

### 2. Device Probe (Trực tiếp từ shell Android máy farm)
- **Kiểm tra socket TCP:**
  `adb -s <serial> shell "echo | toybox nc -w 3 192.168.110.2 <PORT>; echo exit_code=\$?"`
  (0 = OPEN, 1 = TIMEOUT/REFUSED).
- **Kiểm tra HTTP Egress thô:**
  `adb -s <serial> shell 'printf "GET http://api.ipify.org/ HTTP/1.1\r\nHost: api.ipify.org\r\nProxy-Connection: close\r\n\r\n" | toybox nc -w 5 -W 5 192.168.110.2 <PORT>'`
  (Kiểm tra phản hồi HTTP/1.1 200 OK và IP public).
- **Kiểm tra HTTPS Tunnel CONNECT:**
  `adb -s <serial> shell 'printf "CONNECT www.tiktok.com:443 HTTP/1.1\r\nHost: www.tiktok.com:443\r\nProxy-Connection: close\r\n\r\n" | toybox nc -w 5 -W 5 192.168.110.2 <PORT>'`
  (Bắt buộc trả `HTTP/1.1 200 Connection established`).

### 3. Device System State (Kiểm tra bẫy hệ điều hành)
- **Wi-Fi Validation:** `adb shell "dumpsys connectivity | grep -E 'NetworkAgentInfo.*WIFI|lastValidated'"` ➔ Phải có `lastValidated: true`, `Score: 60`.
- **Đồng hồ hệ thống:** `adb shell "date; settings get global auto_time"` ➔ Năm hiện tại (2026), `auto_time: 1` (tránh bẫy lệch giờ năm 2016 gây lỗi SSL).

### 4. TikTok Live Check
- Mở app TikTok (`monkey -p com.ss.android.ugc.trill -c android.intent.category.LAUNCHER 1`).
- Chụp ảnh màn hình (`screencap`) và OCR nhanh: Đảm bảo app load feed bình thường, không dính banner *"Không có kết nối Internet"*, *"Đã xảy ra lỗi"* hoặc nút *"Thử lại"* (`dd9`/`dcj`).
