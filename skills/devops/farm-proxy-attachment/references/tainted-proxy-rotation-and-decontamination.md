# Tainted Proxy Rotation & Decontamination Runbook

## Overview
When accounts (Codex, ChatGPT-Web, TikTok, Google) suffer platform-level bans or deactivations (`account_deactivated`, checkpoints), their associated proxy endpoints become "tainted". Continuing to route new or surviving accounts through these same egress IPs risks association bans.

This runbook defines the exact protocol to trace tainted ports across GPM and OmniRoute, rotate IPs across both MobiProxy and MikroTik clusters safely, and verify IP deltas.

---

## 1. Tainted Port Identification Protocol
To locate all ports historically associated with banned accounts:
1. **GPM Profile Audit**:
   Query `C:\Users\Kibe\AppData\Local\Programs\GPMLogin\profile\profile_data.db`:
   ```python
   import sqlite3, json, re
   conn = sqlite3.connect(r'C:\Users\Kibe\AppData\Local\Programs\GPMLogin\profile\profile_data.db')
   rows = conn.execute('SELECT Name, JsonData FROM Profiles').fetchall()
   for name, j in rows:
       d = json.loads(j) if j else {}
       proxy_str = d.get('Proxy', '')
       # Match against banned email set
   ```
2. **OmniRoute Audit**:
   Query `C:\Users\Kibe\.omniroute\storage.sqlite` table `proxy_logs`:
   ```sql
   SELECT DISTINCT proxy_host, proxy_port FROM proxy_logs WHERE account IN (<banned_ids>);
   ```
3. Group identified ports into:
   - **MobiProxy cluster**: `test.taadaa.click:5101..5138`
   - **MikroTik PPPoE cluster**: `mirotik1.taadaa.click:10001..10035` (`192.168.110.2`)

---

## 2. MobiProxy 4G Cluster Rotation (`test.taadaa.click`)

### Quy tắc Cổng 5101 (DDNS Anchor & Xoay Thủ Công Khi Cần)
- **Trong watchdog/auto-healer tự động:** DUY TRÌ BẢO VỆ Cổng 5101 (`PROTECTED_HEAL_PORTS = {5101}`). Tuyệt đối không để script auto-healer chạy ngầm tự ý recreate 5101 vì việc reset liên tục trong nền có thể gây chập chờn phân giải DDNS `test.taadaa.click` cho toàn cụm.
- **Khi xoay thủ công / tẩy sạch IP theo lệnh User:** Cổng 5101 **HOÀN TOÀN ĐỔI ĐƯỢC BÌNH THƯỜNG**. Khi gọi `/proxy_recreat` cho cổng 5101, modem 4G quay số lại và daemon DDNS trên box sẽ tự động đẩy IP mới lên DNS trong vòng 15 giây.
- **Quy trình nghiệm thu khi xoay 5101:**
  1. Trigger `/proxy_recreat?proxy=test.taadaa.click:5101&token=...`
  2. Chờ 15s để modem hoàn tất quay số và cập nhật DDNS.
  3. Kiểm tra phân giải domain: `socket.gethostbyname('test.taadaa.click')` phải khớp với IP egress mới của port 5101.
  4. Probe lại các cổng khác (5102, 5104, 5128...) đảm bảo thông tuyến 100%.

### Execution Procedure for Ports `5102..5138`:
1. Call `/proxy_recreat` endpoint:
   `http://test.taadaa.click/proxy_recreat?proxy=test.taadaa.click:{port}&token={token}`
2. **Pacing**: Introduce a mandatory **2.0s – 2.5s delay** between successive API calls. Box OpenWrt (MT7621) has limited CPU/RAM; burst requests cause PHP-FPM crashes (`502 Bad Gateway`).
3. **Settling Time**: Wait **15.0 seconds** post-command for the 4G modem to complete redial and register a new public IP.

---

## 3. MikroTik PPPoE Cluster Rotation (`mirotik1.taadaa.click` / `192.168.110.2`)

### Port-to-Interface Mapping
- Ports `10001..10035` map 1-to-1 to RouterOS interfaces `pppoe-out1..pppoe-out35`.
- Retrieve `.id` references via REST API: `GET http://192.168.110.2:9090/rest/interface/pppoe-client`.

### Mandatory 35-40s BRAS Session Clearing Window
- **Root Cause Trap**: Disabling and re-enabling a PPPoE interface in `< 15 seconds` causes the ISP BRAS (Viettel/FPT) to keep the existing session lease active, returning the **exact same public IP**.
- **Correct Sequence**:
  1. Disable target interfaces via PATCH:
     `PATCH /rest/interface/pppoe-client/{id}` with `{"disabled": true}`.
  2. **Sleep 35 to 40 seconds** to force the BRAS to tear down the subscriber session.
  3. Re-enable target interfaces via PATCH:
     `PATCH /rest/interface/pppoe-client/{id}` with `{"disabled": false}`.
  4. Wait 8 seconds for interface IP acquisition (`/rest/ip/address`).

### Post-Rotation Container Restart
When PPPoE WAN interfaces drop and re-establish, active TCP sockets in containerized proxies break (`502 Bad Gateway` / `Connection forcibly closed`).
- **Sing-box container (`*6`)**: Restart via `POST /rest/container/stop` -> wait 3s -> `POST /rest/container/start`.
- **3proxy container (`*3`)**: Verify running state and restart if stopped.

---

## 4. Double Verification & Audit Protocol
Never declare rotation complete without an auditable delta check:
1. **Pre-rotation**: Record `baseline_ips = {port: get_egress_ip(port)}`.
2. **Post-rotation**: Probe each port via HTTP/HTTPS proxy CONNECT (`api.ipify.org`).
3. **Audit Assertion**: Ensure `new_ip != old_ip` and `new_ip` is not an error string.
4. Output a clean markdown table showing `Type | Port | Old IP | New IP | Status (CHANGED)`.
