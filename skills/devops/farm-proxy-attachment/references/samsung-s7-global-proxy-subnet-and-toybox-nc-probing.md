# Samsung S7 Farm: Global HTTP Proxy, Wi-Fi Subnets & Toybox NC Probing

## 1. Network Topology & Subnet Mismatch Pitfall

### Topology & IP Gateway
- **Dàn Kibe (80 máy Samsung S7):**
  - **Máy 01..40:** Kết nối Wi-Fi **`kibe 1`** $\rightarrow$ Subnet `192.168.10.0/24`.
  - **Máy 41..80:** Kết nối Wi-Fi **`kibe 2`** $\rightarrow$ Subnet `192.168.110.0/24`.
  - **Proxy Gateway IP:** **`192.168.110.2`** (IP này có thể định tuyến thông suốt từ cả 2 mạng Wi-Fi `kibe 1` và `kibe 2`).
  - **Cổng Proxy gán tĩnh:** Máy $N$ $\rightarrow$ `192.168.110.2:20000+N` (20001..20080).

### Lỗi lệch Subnet ban đầu (`192.168.10.254` vs `192.168.110.x`)
- Khi proxy trỏ về `192.168.10.254`:
  - Các máy ở dải `192.168.10.x` kết nối bình thường.
  - Các máy ở dải `192.168.110.x` (như Máy 79) bị **`ERR_CONNECTION_TIMED_OUT`** do `192.168.10.254` không có route từ `192.168.110.x`.
- **Khắc phục chuẩn:** Trỏ toàn bộ dàn về IP **`192.168.110.2:20001..20080`**.

---

## 2. Gán Global Proxy & Tắt Captive Portal

Khi sử dụng gateway proxy nội bộ thay thế ViChanger, chạy 3 lệnh ADB sau trên từng máy:
```bash
# 1. Gán Proxy toàn cục
adb -s <serial> shell settings put global http_proxy 192.168.110.2:<20000+N>

# 2. Tắt kiểm tra Captive Portal (tránh cảnh báo "Mạng Wi-Fi không có Internet" trên Android)
adb -s <serial> shell settings put global captive_portal_mode 0
adb -s <serial> shell settings put global captive_portal_detection_enabled 0
```

---

## 3. Test Proxy & Lấy Live Public IP qua Toybox Netcat (NC)

Samsung S7 (Android 8.0) không có sẵn `curl` hay `wget`. Cách nhanh và chuẩn xác nhất để test HTTP Proxy trực tiếp trên thiết bị:
```bash
# Test HTTP GET qua Proxy Port
adb -s <serial> shell 'printf "GET http://api.ipify.org/ HTTP/1.1\r\nHost: api.ipify.org\r\nProxy-Connection: close\r\n\r\n" | toybox nc -w 4 -W 4 -q 1 192.168.110.2 <port>'

# Test HTTPS CONNECT (mô phỏng browser kết nối SSL)
adb -s <serial> shell 'printf "CONNECT www.google.com:443 HTTP/1.1\r\nHost: www.google.com:443\r\n\r\n" | toybox nc -w 4 -W 4 -q 1 192.168.110.2 <port>'
```

### Phân loại trạng thái phản hồi:
- **`200 OK` + `<IP>`:** Proxy hoạt động bình thường, Public IP chuẩn.
- **`502 Bad Gateway`:** Gateway `192.168.110.2` đang nhận kết nối nhưng Upstream Box/Dcom/MobiProxy của cổng đó đang mất mạng hoặc xoay IP.
- **`nc: Timeout` / rỗng:** Mất kết nối tới Gateway Proxy (lệch subnet, rớt Wi-Fi hoặc tắt radio Wi-Fi).
