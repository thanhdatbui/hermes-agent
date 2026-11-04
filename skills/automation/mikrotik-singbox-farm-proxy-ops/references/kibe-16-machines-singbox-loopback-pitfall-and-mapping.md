# Cạm Bẫy Loopback Port Singbox Inbound/Outbound & Quy Chuẩn Mapping 16 Máy Kibe

## 1. Bản Chất Sự Cố (Root Cause: Self-Loopback Socket Starvation)
- **Hiện tượng:** Toàn bộ batch máy Kibe thuộc dải MikroTik/Khoalee (M33, M34, M36, M38, M71-M79) đồng loạt văng lỗi:
  ```text
  Client.Timeout exceeded while awaiting headers (Get "http://ifconfig.me/ip")
  ```
- **Nguyên nhân:**
  - File Excel `PROXYgandienthoai.xlsx` và cấu hình gộp `singbox_full_160.json` bị điền nhầm outbound target của các máy này thành chính cổng Inbound Singbox:
    ```json
    "tag": "proxy_m33", "server": "192.168.110.2", "server_port": 20033
    ```
  - Khi điện thoại S7 gửi request vào `192.168.110.2:20033`, Singbox container nhận request và lại mở socket kết nối vào chính cổng `20033` của chính nó (vòng lặp vô tận).
  - Nhân Linux trên MikroTik container báo lỗi:
    ```text
    ERROR using outbound/http[proxy_m38]: dial tcp 192.168.110.2:20038: connect: cannot assign requested address
    ```
  - Cạn socket tức thời làm runner preflight bị timeout và kích hoạt Fail-Closed bảo vệ nick.

## 2. Quy Chuẩn Mapping 16 Máy Kibe (Tri-Sync SSOT)
- 16 máy Kibe này KHÔNG chạy MobiProxy Thái Bình (5101..5138), mà chạy trên 7 line MikroTik PPPoE Đà Nẵng + 1 line Khoalee:
  - `M33`: `mirotik1.taadaa.click:10001` (PPPoE out1)
  - `M34`: `mirotik1.taadaa.click:10002` (PPPoE out2)
  - `M35`: `mirotik1.taadaa.click:10003` (PPPoE out3)
  - `M36`: `mirotik1.taadaa.click:10004` (PPPoE out4)
  - `M37`: `mirotik1.taadaa.click:10005` (PPPoE out5)
  - `M38`: `khoalee.duckdns.org:16002`
  - `M71`: `mirotik1.taadaa.click:10006` (PPPoE out6)
  - `M72`: `mirotik1.taadaa.click:10001` (PPPoE out1)
  - `M73`: `mirotik1.taadaa.click:10002` (PPPoE out2)
  - `M74`: `mirotik1.taadaa.click:10003` (PPPoE out3)
  - `M75`: `mirotik1.taadaa.click:10004` (PPPoE out4)
  - `M76`: `khoalee.duckdns.org:16002`
  - `M77`: `mirotik1.taadaa.click:10005` (PPPoE out5)
  - `M78`: `mirotik1.taadaa.click:10006` (PPPoE out6)
  - `M79`: `mirotik1.taadaa.click:10007` (PPPoE out7)
  - `M80`: `mirotik1.taadaa.click:10007` (PPPoE out7)

## 3. Quy Tắc Kiểm Tra Chống Loopback Bắt Buộc (Invariant Anti-Loopback)
- Khi sinh cấu hình Singbox hoặc audit file Excel:
  - BẮT BUỘC kiểm tra: Với mọi máy $m$, outbound `proxy_m{m}` KHÔNG ĐƯỢC PHÉP trỏ vào IP router (`192.168.110.2`) kèm port inbound (`20000 + m` hoặc `20200 + m`).
  - Outbound phải luôn trỏ tới: Upstream MobiProxy (`test.taadaa.click:51xx`), R3G (`tb.taadaa.click:51xx`), 3proxy PPPoE (`mirotik1.taadaa.click:100xx`), hoặc proxy phụ trợ.

## 4. Quy Trình Nạp Cấu Hình & Restart Container Chuẩn Qua RouterOS REST API
- **Sinh file minified:** `generate_singbox_config(..., minified=True)` để giảm payload xuống ~27KB, tránh timeout hoặc lỗi chunking.
- **PATCH trực tiếp qua REST API (Bypass SSH/SFTP dependency):**
  ```python
  import urllib.request, json, base64
  auth = base64.b64encode(b'admin:N0spam@@').decode()
  content = open('D:/Taadaa/AI-Tools/config/singbox_full_160_min.json', encoding='utf-8').read()
  req = urllib.request.Request(
      'http://192.168.110.2:9090/rest/file/*8072575',
      data=json.dumps({'contents': content}).encode('utf-8'),
      headers={'Authorization': f'Basic {auth}', 'Content-Type': 'application/json'},
      method='PATCH'
  )
  urllib.request.urlopen(req, timeout=15)
  ```
- **Restart Container *6 an toàn:**
  - Gửi POST tới `/rest/container/stop` với payload `{".id": "*6"}`.
  - Chờ 5s cho tiến trình dừng hẳn (trạng thái `stopping` kết thúc).
  - Gửi POST tới `/rest/container/start` với payload `{".id": "*6"}`.
  - Xác nhận lại trạng thái qua `GET /rest/container/*6` đạt `status: running`.
- **Canary Probe O(1) kiểm chứng:**
  ```python
  python -c "import urllib.request; req = urllib.request.Request('http://ifconfig.me/ip'); req.set_proxy('192.168.110.2:20033', 'http'); print(urllib.request.urlopen(req, timeout=5).read().decode().strip())"
  ```
  Egress IP trả về đúng IP Public PPPoE Viettel Đà Nẵng là thông mạng 100%.
