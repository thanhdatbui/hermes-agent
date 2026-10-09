# MobiProxy REST API Auto-Healing & Consumer Strict Preflight Enforcement

## 1. Kiến trúc Upstream Proxy & Hiện tượng 502 Bad Gateway trên Sing-box

### Mô hình ghép cặp Proxy trên Farm Kibe (80 máy)
- **Cụm Sing-box nội bộ:** Chạy container tại `192.168.110.2`, mở các cổng inbound `20001` đến `20080` tương ứng Máy 01 đến Máy 80.
- **Tầng Upstream Forwarding:**
  - Một số máy ghép cặp dùng chung line PPPoE trên MikroTik (`mirotik1.taadaa.click:10001..10035`).
  - Một số máy ghép cặp dùng chung modem 4G trên cụm MobiProxy (`test.taadaa.click:5101..5138` gồm 32 cổng chia 4 LAN: 5101..5108, 5111..5118, 5121..5128, 5131..5138; auth `mobi{port - 5100}:TaadaaMobi#2026!`).
  - *Ví dụ thực tế:* Máy 08 (cổng 20008) và Máy 46 (cổng 20046) cùng trỏ về upstream modem `mobi8` tại `test.taadaa.click:5108`. Cổng 5111 dùng user `mobi11` (không phải `mobi9`).

### Bẫy ngầm khi Modem 4G rớt phiên / mất mạng:
1. Cổng Sing-box nội bộ (`192.168.110.2:200xx`) vẫn **OPEN** (`connect_ex == 0`).
2. Điện thoại vẫn kết nối Wi-Fi LAN và ping ICMP tới gateway Ruijie `192.168.110.1` thành công 100%.
3. Nhưng khi gửi HTTP request qua proxy, Sing-box không kết nối được upstream 4G nên trả về **`HTTP/1.1 502 Bad Gateway`** hoặc ngắt socket `Connection reset by peer (WinError 10054)`. Thiết bị thực chất hoàn toàn không có internet.
4. **Tải dồn Multiplexing (2-3 máy/modem)**: Khi nhiều máy cùng chạy batch upload video / lướt feed, số lượng connection TCP dồn lên 1 modem 4G làm tiến trình 3proxy trên box bị crash/đóng cổng (`Connection Refused`), sinh lỗi giả mạo "Không có kết nối" trên TikTok.

---

## 2. MobiProxy Control Web (`test.taadaa.click`) & REST API Specifications

- **Web Dashboard:** `http://test.taadaa.click` (Version: Web v3.0.61)
- **Mật khẩu quản trị:** `n0spam@@`
- **API Token (Bearer / Query param):** `mpx_b0feb089e0a6b5224043d4c7bf6de34dc6a3a8ec552745aa`

### Các Endpoints Quản trị Trực tiếp:
1. **Lấy danh sách và trạng thái toàn bộ 32 proxy modem:**
   - `GET http://test.taadaa.click/proxy_getlist?token={token}`
   - Trả về JSON:
     ```json
     {
       "listproxy": "json",
       "result": [
         {
           "ip_public": "116.104.215.29",
           "proxyv4": "test.taadaa.click:5108",
           "proxyv6": "test.taadaa.click:5208",
           "uptime": "1d18h",
           "source": "Lan1",
           "status": "true"
         }
       ]
     }
     ```
   - Khi modem bị sập/mất kết nối: `status` trả về `"false"`, `ip_public` rỗng hoặc mang ký tự gạch ngang `—`.

2. **Kiểm tra trạng thái 1 proxy cụ thể:**
   - `GET http://test.taadaa.click/proxy_check?proxy=test.taadaa.click:{PORT}&token={token}`
   - Trả về: `{"result":"ok","content":"proxy_ok"}` hoặc `{"result":"ok","content":"proxy_false"}`.
   - ⚠️ **Cạm bẫy False-Positive:** `proxy_check` có thể trả về `"proxy_ok"` và `proxy_getlist` trả `"status": "true"` khi modem 4G có IP WAN, nhưng cổng TCP listener (51xx) trên host lại bị crash/đóng (`Connection Refused`). Do đó, kiểm tra sức khỏe proxy bắt buộc phải kèm probe TCP socket (`socket.connect_ex` hoặc `curl -s -m 3 -x http://test.taadaa.click:{PORT}`) trực tiếp từ máy kiểm tra.

3. **Tự động kích hoạt lại / Recreate modem bị rớt (Auto-Heal):**
   - `GET http://test.taadaa.click/proxy_recreat?proxy=test.taadaa.click:{PORT}&token={token}`
   - Trả về: `{"result":"ok","content":"RECREAT_PROXY_DONE"}`.
   - Modem 4G sẽ ngắt phiên cũ, quay số kết nối lại và cấp phát IP WAN mới trong 3–7 giây.

4. **Reset hàng loạt:**
   - `GET http://test.taadaa.click/proxy_rs_all_1?token={token}` (Reset toàn bộ 32 modem).
   - `GET http://test.taadaa.click/proxy_rs_all_2?token={token}` (Reset toàn bộ trừ cổng đầu).

---

## 3. Tool Tự Phục Hồi: `mobiproxy_auto_healer.py`

Được đặt tại: `D:\Taadaa\AI-Tools\scripts\mobiproxy_auto_healer.py`.
- **Cấu trúc 32 cổng thực tế (Cạm bẫy tuyến tính):**
  - Cụm gồm 32 modem phân bố thành 4 LAN x 8 cổng:
    * Lan1: `5101..5108`
    * Lan2: `5111..5118` (bỏ qua 5109..5110)
    * Lan3: `5121..5128` (bỏ qua 5119..5120)
    * Lan4: `5131..5138` (bỏ qua 5129..5130)
  - ⚠️ Tuyệt đối không dùng vòng lặp `5101..5132` vì sẽ probe nhầm các cổng không tồn tại (5109, 5110, 5119, 5120, 5129, 5130) và bỏ sót các cổng từ 5133 đến 5138.
- **Cơ chế kiểm tra sức khỏe 2 lớp (Strict 2-Layer Health Check):**
  - **Lớp 1 (API Status):** Lấy danh sách từ `/proxy_getlist`, yêu cầu `status == "true"` và `ip_public` không rỗng/không gạch ngang.
  - **Lớp 2 (TCP Socket Listener):** Quét song song đa luồng (`ThreadPoolExecutor`) bằng `socket.connect_ex((host, port))` với timeout <= 1.5s để bắt triệt để cạm bẫy false-positive khi web API báo true nhưng listener 51xx bị sập / connection refused.
- **Quy trình Auto-Heal:**
  - Phát hiện DEAD $\rightarrow$ gửi `GET /proxy_recreat?proxy=test.taadaa.click:{PORT}&token={token}` $\rightarrow$ chờ 5s $\rightarrow$ probe lại TCP socket và HTTP live egress (`http://api.ipify.org` với auth `mobi{port-5100}:TaadaaMobi#2026!`) xác nhận hồi sinh.
- **Ghi log & Thống kê tần suất:**
  - Event log: `D:\Taadaa\AI-Tools\logs\mobiproxy_healer.log`
  - Stats JSON: `D:\Taadaa\AI-Tools\logs\mobiproxy_stats.json` (ghi nhận `die_count`, `last_die_time`, `last_die_reason`, `heal_success_count`, `heal_failure_count`, `last_known_ip`, `current_status`).
- **CLI Commands:**
  - Quét 1 lần và tự phục hồi:
    ```bash
    python D:/Taadaa/AI-Tools/scripts/mobiproxy_auto_healer.py --check-and-heal
    ```
  - Quét kiểm tra không can thiệp:
    ```bash
    python D:/Taadaa/AI-Tools/scripts/mobiproxy_auto_healer.py --check-only
    ```
  - Chạy ngầm định kỳ:
    ```bash
    python D:/Taadaa/AI-Tools/scripts/mobiproxy_auto_healer.py --daemon --interval 60
    ```
  - Xem bảng thống kê tần suất die / heal:
    ```bash
    python D:/Taadaa/AI-Tools/scripts/mobiproxy_auto_healer.py --stats
    ```
  - Xuất dữ liệu JSON:
    ```bash
    python D:/Taadaa/AI-Tools/scripts/mobiproxy_auto_healer.py --json
    ```

---

## 4. Hermes Cronjob Watchdog Integration & Operator Communication

1. **Watchdog tự động (Hermes Cronjob):**
   - Tên job: `mobiproxy-auto-healer-watchdog`
   - Chu kỳ: Mỗi phút (`*/1 * * * *`, `no_agent: true`).
   - Launcher script: `C:\Users\Kibe\AppData\Local\hermes\scripts\cron_mobiproxy_healer.py`.
   - Vận hành: Chạy ngầm độc lập với phiên chat, không chiếm CPU của agent, liên tục cập nhật số lần die/heal vào `mobiproxy_stats.json`.
2. **Quy tắc giao tiếp với User về "Change IP":**
   - Khi user hỏi *"Là phải change ip trên port X à?"* hoặc *"Thì cái mày làm chả là change ip thì là gì"*:
   - Thừa nhận và xác nhận thẳng thắn: **Đúng, bản chất `proxy_recreat` là reset modem để change IP và khởi động lại dịch vụ proxy mở lại cổng**.
   - CẤM TUYỆT ĐỐI tranh luận ngữ nghĩa học thuật rườm rà (như phân trần "không hẳn là đổi IP mà là..."). User cần sự ngắn gọn, trực diện và đồng điệu với thuật ngữ thực tế của farm.

---

## 5. Consumer Strict Preflight Parity: Quy tắc Bắt buộc giữa các Repo

Mọi repo consumer (`Tiktok_Reg`, `tiktok-luot nuoi acc`, `register gmail`) bắt buộc phải đồng bộ chuẩn chốt chặn:

```python
vpn_required = serial_is_mapped_in_workbook(MAPPING_PATH, serial)
vpn_status = require_android_vpn(adb, required=vpn_required, verify_live_ip=True)

status_res = getattr(vpn_status, "result", str(vpn_status)).upper()
proxy_ip = str(getattr(vpn_status, "proxy_ip", "") or "").strip()

if vpn_required and (
    not getattr(vpn_status, "allowed", False)
    or not getattr(vpn_status, "connected", False)
    or not proxy_ip
):
    evidence = getattr(vpn_status, "error", "") or "live proxy IP proof missing"
    raise ConsumerPreflightError(f"VPN verification failed: {evidence}")
```

### Cấm tuyệt đối:
1. Không được chỉ kiểm tra `vpn_status.allowed` chung chung mà bỏ qua `vpn_status.proxy_ip`.
2. Không để fallback ping LAN Wi-Fi che mờ lỗi `502 Bad Gateway` của proxy upstream.
3. Nếu proxy chết hoặc `proxy_ip` rỗng: lập tức fail-closed `STOPPED: [PREFLIGHT_PROXY]`, nhả `device_lock` và ngắt ngay lập tức, tuyệt đối không khởi động app automation.
