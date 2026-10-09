# Triển khai Tinyproxy HTTP Proxy có xác thực trên VPS làm Egress cho Telegram Gateway

> ⚠️ **CẢNH BÁO QUAN TRỌNG (DIRECT FPT vs PROXY):**
> Trước khi cấu hình `TELEGRAM_PROXY`, BẮT BUỘC kiểm tra kết nối Direct FPT: `python -c "import httpx; print(httpx.get('https://api.telegram.org/', timeout=10).status_code)"`.
> Nếu Direct FPT trả về status 302 và latency < 1.0s (như máy Admin), **TUYỆT ĐỐI KHÔNG DÙNG PROXY**.
> Dùng Tinyproxy trên Windows gây rò rỉ hơn 960 socket `CLOSE_WAIT`, cạn kiệt pool 1024 và làm bot treo liên tục. Máy Admin chạy FPT Direct không hề treo. Chỉ kích hoạt proxy khi ISP chặn triệt để cả IP và DNS.

Tài liệu hướng dẫn triển khai, cấu hình bảo mật và kiểm định proxy HTTP có xác thực BasicAuth trên Linux VPS (Ubuntu/Debian) phục vụ định tuyến Telegram Gateway của Hermes thoát khỏi bóp nghẽn ISP.

---

## 1. Cài đặt và cấu hình Tinyproxy trên VPS Linux

### 1.1. Cài đặt package
```bash
DEBIAN_FRONTEND=noninteractive apt-get update -qq
DEBIAN_FRONTEND=noninteractive apt-get install -y -qq tinyproxy
```

### 1.2. Cấu hình bảo mật `/etc/tinyproxy/tinyproxy.conf`
Tạo bản backup trước khi sửa:
```bash
cp /etc/tinyproxy/tinyproxy.conf /etc/tinyproxy/tinyproxy.conf.bak
```

Các tham số cần thiết:
1. **Đổi Port mặc định (tránh bot scan port 8888):**
   ```text
   Port 18888
   ```
2. **Cơ chế Allow & BasicAuth (BẪY QUAN TRỌNG):**
   - Trong Tinyproxy, nếu tồn tại bất kỳ dòng `Allow <IP>` nào thì mặc định mọi IP khác sẽ bị `DENY`.
   - Để cho phép client kết nối từ WAN bất kỳ nhưng BẮT BUỘC xác thực: comment out toàn bộ `Allow 127.0.0.1` và `Allow ::1`, đồng thời thêm `BasicAuth`:
   ```text
   #Allow 127.0.0.1
   #Allow ::1
   BasicAuth <PROXY_USER> <PROXY_PASS>
   ```
3. **Ẩn Header Proxy (Stealth mode):**
   ```text
   DisableViaHeader Yes
   ```

### 1.3. Khắc phục lỗi quyền ghi Log trên Ubuntu/Debian
Khi cài qua `apt`, thư mục `/var/log/tinyproxy` thường thuộc sở hữu của `root:root`. Khi daemon chạy dưới user `tinyproxy`, daemon sẽ báo lỗi:
`ERROR: Could not create log file /var/log/tinyproxy/tinyproxy.log: Bad file descriptor` và fallback về syslog.
Xử lý:
```bash
chown -R tinyproxy:tinyproxy /var/log/tinyproxy
```

### 1.4. Mở tường lửa UFW và khởi chạy Service
```bash
ufw allow 18888/tcp
systemctl restart tinyproxy
systemctl enable tinyproxy
systemctl status tinyproxy --no-pager
```

---

## 2. Thang kiểm định kết nối (Verification Ladder) từ máy Host

Kiểm tra từ xa từ máy trạm (Windows git-bash hoặc Linux):

1. **Kiểm tra chặn truy cập trái phép (Bắt buộc trả về HTTP 407):**
   ```bash
   curl -s -I -x "http://<VPS_IP>:18888" https://api.telegram.org/
   # Kỳ vọng: HTTP/1.0 407 Proxy Authentication Required
   ```
2. **Kiểm tra kết nối có Auth (CONNECT Tunnel thành công):**
   ```bash
   curl -s -I -x "http://<PROXY_USER>:<PROXY_PASS>@<VPS_IP>:18888" https://api.telegram.org/
   # Kỳ vọng: HTTP/1.0 200 Connection established -> HTTP/1.1 302 Moved Temporarily
   ```
3. **Kiểm tra Egress IP thực tế qua Proxy:**
   ```bash
   curl -s -m 10 -x "http://<PROXY_USER>:<PROXY_PASS>@<VPS_IP>:18888" https://api.ipify.org
   # Kỳ vọng: Trả về đúng địa chỉ IPv4 của VPS
   ```
4. **Đo độ trễ kết nối (Latency Probe):**
   ```bash
   curl -o /dev/null -s -w "TCP: %{time_connect}s | TLS: %{time_appconnect}s | Total: %{time_total}s\n" \
     -x "http://<PROXY_USER>:<PROXY_PASS>@<VPS_IP>:18888" https://api.telegram.org/
   ```

---

## 3. Cập nhật và Reload Hermes Gateway an toàn

1. **Ghi biến môi trường vào `$HERMES_HOME/.env`:**
   ```text
   TELEGRAM_PROXY=http://<PROXY_USER>:<PROXY_PASS>@<VPS_IP>:18888
   ```
   *Lưu ý:* Nếu user hoặc pass có ký tự đặc biệt như `@`, bắt buộc URL-encode thành `%40`.
2. **Đồng bộ file mẫu deploy:**
   Kiểm tra `deploy/hermes-home/.env` trong repo git, đảm bảo chỉ lưu sanitized placeholder:
   `# TELEGRAM_PROXY=http://<PROXY_USER>:<PROXY_PASS>@<PROXY_HOST>:<PROXY_PORT>`
3. **Kích hoạt One-Shot Idle Watcher (Zero-Disruption):**
   Không chạy lệnh restart trực tiếp trong session đang hoạt động để tránh kill parent. Kích hoạt watcher chạy ngầm:
   ```powershell
   powershell.exe -NoProfile -Command "Start-Process powershell.exe -ArgumentList '-NoProfile -ExecutionPolicy Bypass -File C:\Users\Kibe\AppData\Local\hermes\scripts\restart-when-idle.ps1' -WindowStyle Hidden"
   ```

---

## 4. Hiện tượng Silent TCP Stall & Rò rỉ CLOSE_WAIT qua VPS Proxy (Forensics & Phòng tránh)

Ngay cả khi đã đẩy qua VPS Proxy (Singapore), bot Telegram vẫn có thể bị "treo ngầm" 6–8 phút do đặc thù kiến trúc 2 chặng:

### 4.1. Cơ chế kẹt socket 2 chặng (PC VN $\rightarrow$ VPS SGP $\rightarrow$ Telegram DC5)
* **VPS giải quyết được gì:** Bypass triệt để lỗi FPT/Viettel bóp DNS (`getaddrinfo failed`) hoặc drop dải IP gốc `api.telegram.org` (`149.154.166.110`).
* **Chặng dễ tổn thương (Chặng 1: PC $\rightarrow$ VPS):** Kết nối TCP giữa máy tính local (Hải Phòng/VN) và VPS Doravo (Singapore) vẫn chạy qua đường truyền quốc tế của ISP nội địa.
* **Hiện tượng Silent TCP Stall:** Khi đường truyền quốc tế chập chờn hoặc rớt gói, socket persistent HTTP CONNECT phục vụ long-poll (`getUpdates`) bị rơi vào trạng thái nửa mở (half-open/stall ngầm):
  1. Máy local và Tinyproxy vẫn coi kết nối là ESTABLISHED.
  2. Server Telegram đẩy update về VPS, nhưng gói tin từ VPS về local bị rớt/nghẽn.
  3. **Điểm mù Heartbeat:** `bot.get_me()` dùng connection pool riêng nên vẫn trả về 200 OK (<200ms) qua VPS; còn `get_webhook_info().pending_update_count` luôn trả về 0 trong chế độ Polling $\rightarrow$ Heartbeat không phát hiện được socket `getUpdates` đã chết.
  4. Socket bị ngâm tới khi TCP keepalive của OS hoặc timeout của Tinyproxy chạm ngưỡng (~6–8 phút) mới reset và kéo dồn tin nhắn về (`Flushing text batch`).

### 4.2. Rò rỉ hàng trăm socket `CLOSE_WAIT` tới Port Proxy
* **Triệu chứng:** Khi chạy đa session song song (10–15 sessions), số lượng socket tới `<VPS_IP>:<PROXY_PORT>` ở trạng thái `CloseWait` tăng vọt (700–800+ sockets), áp sát trần `HERMES_TELEGRAM_HTTP_POOL_SIZE=1024`.
* **Lệnh kiểm tra định lượng:**
  ```powershell
  $conns = Get-NetTCPConnection -RemoteAddress "<VPS_IP>" -OwningProcess <pid_gateway> -ErrorAction SilentlyContinue
  $conns | Group-Object State | Select Name, Count
  ```
* **Nguyên nhân:** Tinyproxy đóng các kết nối idle (`Timeout 600`), gửi TCP FIN về máy Windows. Phía client Windows chuyển sang `CLOSE_WAIT` nhưng pool client của HTTPX/httpcore chỉ thu hồi socket khi có request mới tái sử dụng hoặc khi pool đóng hẳn.

### 4.3. Biện pháp siết chặt và xử lý triệt để
1. **Cấu hình lại Tinyproxy trên VPS (`/etc/tinyproxy/tinyproxy.conf`):**
   - Giảm `Timeout 600` xuống `Timeout 60` (hoặc `30`) để Tinyproxy chủ động cắt sớm các socket rỗng, không ngâm 10 phút.
   - Đảm bảo `MaxClients 100` được nâng lên `MaxClients 200` nếu farm có nhiều node cùng kết nối.
2. **Siết chặt và nạp Keepalive Limits vào Connection Pool (`_http_client_limits.py` & `.env`):**
   - Bản chất rò rỉ: `httpcore.AsyncConnectionPool` thu hồi socket dạng *thụ động (lazy)* — chỉ dọn socket hết hạn/nhận FIN khi có request mới enqueue vào pool. Với `HERMES_TELEGRAM_HTTP_POOL_SIZE=1024`, socket rác tích lũy áp sát trần gây `PoolTimeout`.
   - Cấu hình chuẩn trong `$HERMES_HOME/.env`:
     ```bash
     HERMES_TELEGRAM_HTTP_POOL_SIZE=256        # Hạ từ 1024 xuống 256 để tránh phình socket rác
     HERMES_TELEGRAM_HTTP_POOL_TIMEOUT=20.0
     HERMES_TELEGRAM_HTTP_CONNECT_TIMEOUT=10.0
     HERMES_TELEGRAM_HTTP_READ_TIMEOUT=25.0
     HERMES_TELEGRAM_HTTP_WRITE_TIMEOUT=25.0
     HERMES_GATEWAY_HTTPX_KEEPALIVE_EXPIRY=2.0 # Đóng idle keepalive sau 2s
     HERMES_GATEWAY_HTTPX_MAX_KEEPALIVE=10     # Giới hạn tối đa 10 idle connections
     ```
   - Đảm bảo `httpx.Limits(max_connections=..., max_keepalive_connections=10, keepalive_expiry=2.0)` được inject đúng vào `httpx_kwargs` của cả `request` và `get_updates_request` trong `adapter.py`.
3. **Cơ chế giật đứt Silent TCP Stall $\le$ 25s (Poll Activity Watchdog):**
   - Vấn đề: `get_webhook_info().pending_update_count` luôn trả về 0 trong chế độ polling (điểm mù). Socket `getUpdates` bị drop ngầm sẽ bị ngâm tới 6–8 phút theo TCP timeout của Windows OS.
   - Giải pháp: Tạo biến theo dõi `self._last_poll_activity = time.monotonic()` cập nhật mỗi khi nhận batch update hoặc khi một vòng poll 10s kết thúc bình thường.
   - Trong `_polling_heartbeat_loop` (chạy mỗi 15s): Nếu `time.monotonic() - self._last_poll_activity > 25.0`, xác định socket long-poll đã stall. Chủ động gọi `get_updates_request._client.aclose()` hoặc `_drain_polling_connections()` để giật đứt TCP socket tại local và buộc PTB tái kết nối ngay lập tức, dọn dẹp tin nhắn dồn ứ trong vòng $\le$ 25s thay vì chờ 8 phút.
4. **Giải pháp tối ưu miễn nhiễm 100% (Webhook Mode):**
   - Chuyển từ Polling sang Webhook (`TELEGRAM_WEBHOOK_URL=https://.../telegram`) qua Cloudflare Tunnel. Khi có tin nhắn, Telegram chủ động POST về máy local, loại bỏ hoàn toàn nhu cầu duy trì persistent TCP socket long-poll xuyên quốc gia.
