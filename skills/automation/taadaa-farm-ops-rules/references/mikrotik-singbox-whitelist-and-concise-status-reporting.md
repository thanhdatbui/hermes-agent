# MikroTik Anti-Scan Whitelist (Singbox Container) & Kỷ luật Báo Cáo Trực Diện

## 1. Kỷ Luật Giao Tiếp: Báo Cáo Tình Trạng Mạng / Proxy (User Steering)
- **Tình huống:** Khi user hỏi tình trạng kết nối proxy ("h máy connect proxy đó đã xài đc chưa", "mạng thông chưa?").
- **Yêu cầu:** 
  - Báo cáo **CỰC KỲ NGẮN GỌN & TRỰC DIỆN**.
  - Tách rõ 2 đối tượng độc lập: **PC Kibe** và **Dàn Samsung S7**.
  - Khẳng định ngay: **ĐÃ XÀI ĐƯỢC** hay **CHƯA XÀI ĐƯỢC** ở dòng đầu tiên.
  - Kèm bằng chứng 1-2 dòng (Test HTTPS qua proxy ra IP public nào).
  - **CẤM:** Giải thích dông dài, tường thuật quá trình debug, dump log kỹ thuật trước khi trả lời câu hỏi cốt lõi của user.

---

## 2. Kiến Trúc Proxy Farm: MikroTik (3proxy) ↔ Singbox Container ↔ Dàn S7

### Mô hình luồng dữ liệu (Data Flow):
```
[Dàn S7: M33-M37, M71-M80] (WiFi 192.168.110.x / 192.168.10.x)
       ↓ (HTTP/SOCKS vào Port 20033-20037, 20071-20080)
[Singbox Container] (IP: 172.17.0.2 - Subnet: 172.17.0.0/16)
       ↓ (Upstream HTTP Proxy vào Port 10001-10007)
[MikroTik 3proxy / RouterOS] (Forwarding sang pppoe-out1..pppoe-out35)
       ↓
[Internet / TikTok]
```

### Bẫy Chết Người (Critical Firewall Pitfall):
- MikroTik triển khai firewall chống scan cổng proxy ngoài WAN:
  - Rule: `ALLOW_FPT_LAN_PROXY_PORTS` (chain=forward, accept tcp, `src-address-list=FPT_LAN`, dst-port=10001-10035,20001-20080)
  - Rule ngay sau: `DROP_EXTERNAL_PROXY_PORTS` (chain=forward, drop tcp, dst-port=10001-10035,20001-20080)
- **Nguyên nhân sự cố:**
  - Nếu `FPT_LAN` chỉ chứa `192.168.110.0/24` và `192.168.10.0/24`, các kết nối từ **Singbox container (`172.17.0.0/16`)** đi vào các port `10001-10007` sẽ bị coi là external và **rơi vào `DROP_EXTERNAL_PROXY_PORTS`**.
  - Hậu quả: Toàn bộ máy trỏ qua Singbox sang line PPPoE MikroTik (`M33–M37`, `M71–M80`) đều bị ngắt kết nối mạng ngay lập tức (`WinError 10054 / Connection forcibly closed by remote host`).
- **Quy tắc bất biến:**
  - `FPT_LAN` **BẮT BUỘC** phải có đủ 4 entries:
    1. `192.168.110.0/24` (LAN Ruijie Switch / PC Kibe / Phone WiFi)
    2. `192.168.10.0/24` (Subnet Farm phụ / Gateway phone)
    3. `172.17.0.0/16` (**Singbox Container** — cổng vào 200xx forward sang 100xx)
    4. `127.0.0.1` (Local loopback)

---

## 3. RouterOS REST API Quirks & Quy Tắc Sửa Firewall

1. **Không PATCH giá trị rỗng để clear field:**
   - Trong RouterOS REST API (port 9090), gửi `PATCH {"src-address": ""}` sẽ bị trả lỗi `HTTP Error 400: Bad Request`.
   - Muốn xóa điều kiện: Gọi `DELETE /ip/firewall/filter/<id>` rồi `PUT /ip/firewall/filter` tạo lại rule sạch, sau đó dùng `POST /ip/firewall/filter/move` để xếp đúng thứ tự trước rule DROP.
2. **Không kết hợp cả `src-address` và `src-address-list`:**
   - Nếu đã dùng `src-address-list=FPT_LAN`, tuyệt đối không khai báo thêm `src-address` (nếu có sẽ là phép AND khiến rule không match danh sách).
3. **Kiểm tra NAT trùng lặp khi PUT:**
   - Khi thêm DST-NAT rules qua REST API, phương thức `PUT` luôn tạo mới record (không idempotent như mong muốn). Bắt buộc kiểm tra trùng lặp (`len(dstnats)`) trước khi tạo để tránh bão rules.
