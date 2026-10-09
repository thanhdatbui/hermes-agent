# MikroTik Anti-Scan Whitelist (Singbox Container 172.17.0.0/16) & Kỷ luật Báo Cáo

## 1. Kiến Trúc Singbox Upstream sang MikroTik PPPoE Line
- **Cấu hình Singbox (`D:/Taadaa/AI-Tools/config/singbox_config.json`):**
  - Cụm `M33–M37` (port `20033–20037`) và `M71–M80` (port `20071–20080`) được cấu hình route outbound sang `mirotik1.taadaa.click:10001–10007` (user/pass: `admin@1:admin@1`).
  - Mỗi port 10001–10007 tương ứng với 1 đường PPPoE vật lý (`pppoe-out1` .. `pppoe-out7`).
- **Luồng dữ liệu kết nối:**
  1. Phone S7 (`192.168.110.x`) gửi request HTTP/SOCKS tới Singbox container port `200xx` trên MikroTik (`192.168.110.2`).
  2. Singbox container (`veth-singbox`, IP `172.17.0.2/16`) mở kết nối TCP upstream tới `192.168.110.2:1000x` (hoặc qua domain `mirotik1.taadaa.click:1000x`).
  3. MikroTik RouterOS chuyển tiếp traffic qua firewall filter `forward` chain sang `dockers_proxy` (3proxy) và đi ra interface `pppoe-outX`.

---

## 2. Bẫy Firewall Drop Upstream (Critical Anti-Scan Pitfall)
- **Firewall Whitelist (`FPT_LAN`):**
  - MikroTik sử dụng address-list `FPT_LAN` và rule:
    ```routeros
    /ip firewall filter add chain=forward action=accept protocol=tcp src-address-list=FPT_LAN dst-port=10001-10035,20001-20080 comment=ALLOW_FPT_LAN_PROXY_PORTS
    /ip firewall filter add chain=forward action=drop protocol=tcp dst-port=10001-10035,20001-20080 comment=DROP_EXTERNAL_PROXY_PORTS
    ```
- **Sự cố:**
  - Nếu `FPT_LAN` chỉ có `192.168.110.0/24` và `192.168.10.0/24`, các gói tin xuất phát từ **Singbox container (`172.17.0.2`)** không nằm trong whitelist `FPT_LAN`.
  - Gói tin TCP SYN bị `DROP_EXTERNAL_PROXY_PORTS` drop ngay lập tức, hoặc bị reset kết nối (`WinError 10054 / An existing connection was forcibly closed by the remote host`).
  - Kết quả: Toàn bộ 14 máy dùng proxy Singbox trỏ MikroTik bị mất mạng hoàn toàn (`script-blocker` do không tải được profile TikTok, `proxy-vpn` do timeout).
- **Khắc phục vĩnh viễn:**
  - Bắt buộc khai báo subnet container vào `FPT_LAN`:
    ```bash
    curl -X PUT http://192.168.110.2:9090/rest/ip/firewall/address-list \
      -H "Authorization: Basic YWRtaW46TjBzcGFtQEA=" \
      -H "Content-Type: application/json" \
      -d '{"list": "FPT_LAN", "address": "172.17.0.0/16", "comment": "Singbox Container - allowed to use proxy"}'
    ```

---

## 3. Kỷ luật Báo Cáo Trực Diện (User Style Enforcement)
- Khi user hỏi: *"Tóm lại h máy connect proxy đó đã xài đc chưa. Trình bày dài dòng quá. Cả ở s7 lẫn pc kibe"*
- **Nguyên tắc:**
  1. Dòng đầu tiên: Trả lời thẳng **ĐÃ XÀI ĐƯỢC** hay **CHƯA**.
  2. Chia rõ 2 mục: **PC Kibe** và **Dàn Samsung S7**.
  3. Kèm 1-2 dòng bằng chứng thực tế (IP public test HTTPS qua proxy).
  4. Tuyệt đối không phân tích nguyên lý router dài dòng khi user đang cần confirm thông mạng để chạy batch.
