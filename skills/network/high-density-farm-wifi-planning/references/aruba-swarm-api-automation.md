# Aruba Instant OS (Swarm) API Automation Reference

## 1. Web & API Endpoints
* **API URL:** `https://<AP_IP>:4343/swarm.cgi`
* **Web UI URL:** `https://<AP_IP>:4343/` (Port 80/443 redirect to 4343).
* **Protocol:** HTTPS POST, Form URL-encoded data, Header `X-Requested-With: XMLHttpRequest`.

## 2. Authentication Protocol
To log in and acquire a session token (`sid`):
```python
import urllib.request, ssl, urllib.parse, random, xml.etree.ElementTree as ET

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

headers = {
    "User-Agent": "Mozilla/5.0",
    "X-Requested-With": "XMLHttpRequest",
    "Content-Type": "application/x-www-form-urlencoded"
}

def aruba_login(ip, user="admin", password="n0spam@@"):
    payload = {
        "opcode": "login",
        "nosid": "true",
        "user": user,
        "passwd": password,
        "nocache": str(random.random())
    }
    data = urllib.parse.urlencode(payload).encode()
    req = urllib.request.Request(f"https://{ip}:4343/swarm.cgi", data=data, headers=headers)
    res = urllib.request.urlopen(req, context=ctx, timeout=5)
    root = ET.fromstring(res.read().decode("utf-8"))
    sid_node = root.find("data[@name='sid']")
    if sid_node is not None:
        return sid_node.text
    return None
```

## 3. Command Execution

### A. Global / Cluster Configuration (`opcode=config`)
Used for SSID profiles, DHCP scopes, radio profiles:
```python
def aruba_config(ip, sid, cli_commands):
    payload = {
        "opcode": "config",
        "sid": sid,
        "cmd": cli_commands,
        "nocache": str(random.random())
    }
    data = urllib.parse.urlencode(payload).encode()
    req = urllib.request.Request(f"https://{ip}:4343/swarm.cgi", data=data, headers=headers)
    res = urllib.request.urlopen(req, context=ctx, timeout=5)
    return res.read().decode("utf-8")
```

### B. Per-AP Action / Configuration (`opcode=action`)
Used for modifying individual AP settings (AP Name, AP Zone, Static IP):
```python
def aruba_ap_action(vc_ip, target_ap_ip, sid, cli_commands):
    payload = {
        "opcode": "action",
        "ip": target_ap_ip,
        "sid": sid,
        "cmd": cli_commands,
        "nocache": str(random.random())
    }
    data = urllib.parse.urlencode(payload).encode()
    req = urllib.request.Request(f"https://{vc_ip}:4343/swarm.cgi", data=data, headers=headers)
    res = urllib.request.urlopen(req, context=ctx, timeout=5)
    return res.read().decode("utf-8")
```

### C. Inspection / Query Commands (`opcode=show`)
Used for reading live state, client lists, AP lists, and cluster topology:
```python
def aruba_show(ip, sid, cli_commands):
    payload = {
        "opcode": "show",
        "sid": sid,
        "cmd": cli_commands,
        "nocache": str(random.random())
    }
    data = urllib.parse.urlencode(payload).encode()
    req = urllib.request.Request(f"https://{ip}:4343/swarm.cgi", data=data, headers=headers)
    res = urllib.request.urlopen(req, context=ctx, timeout=5)
    return res.read().decode("utf-8")
```

## 4. AP Zone Isolation & Band Locking Recipes

### A. Lock SSID to Zone
```text
wlan ssid-profile kibe1
  zone zone1
exit

wlan ssid-profile kibe2
  zone zone2
exit
```

### B. Lock SSID to Band (5GHz Only / 2.4GHz Only)
Valid band parameters in Aruba InstantOS are `2.4`, `5.0`, or `all`:
```text
wlan ssid-profile kibe1
  rf-band 5.0
exit

wlan ssid-profile kibe2
  rf-band 5.0
exit
```
*(Note: Passing `5.0GHz` or `a` will be rejected with `Invalid Band Specification: <val>. Valid Options 2.4/5.0/all`)*.

### C. Lock AP Hardware to Zone
Sent via `opcode=action, ip=<AP_IP>`:
```text
zonename "zone1"
```
```text
zonename "zone2"
```

### D. Incremental Per-AP Tx Power & Channel Tuning (`opcode=action`)
* **Kỷ luật nâng công suất từ từ (Chống phá sóng chéo):** Khi một AP bị yếu sóng (ví dụ M7 yếu sóng do AP chỉ phát 12 dBm trong khi các AP khác phát 15 dBm), CẤM nâng vọt lên 18–20+ dBm. BẮT BUỘC nâng từng nấc (+2 đến +3 dBm, ví dụ từ `12 dBm` lên `14 dBm` hoặc `15 dBm`) và giữ nguyên kênh tách biệt (ví dụ Ch 36+ vs Ch 100E vs Ch 116).
* **Lệnh gán cứng kênh & công suất cho 1 AP cụ thể (không đụng các AP khác):**
  Sent qua `opcode=action, ip=<target_ap_ip>` tới Virtual Controller:
  ```text
  a-channel 36+ 14
  ```
  *(Cú pháp: `a-channel <channel>[+] <power_dbm>`. Thêm dấu `+` để chỉ định channel bonding trên kênh 36).*
* **Lệnh trả lại quyền điều khiển tự động cho ARM:**
  ```text
  a-channel 0 0
  ```
* **Lệnh điều chỉnh dải công suất ARM toàn cụm (`opcode=config`):**
  ```text
  arm
    min-tx-power 12
    max-tx-power 15
  ```
  *(Cần gửi thêm `commit apply` và `write memory` sau khi config).*

### E. Client & AP Radio Status Inspection (`opcode=show`)
* **Kiểm tra công suất thực tế từng AP qua `show aps`:**
  Tìm cột `radio0 Power (dBm)` và `radio0 Channel`.
* **Kiểm tra thông tin client kết nối qua `show summary`:**
  Bảng `Clients` trong `show summary` chứa đầy đủ: `['MAC', 'Name', 'IP Address', 'ESSID', 'Access Point']`. Cho phép đối soát ngay MAC điện thoại (ví dụ `ac:5f:3e:60:59:1b`) đã liên kết với Access Point nào và có đúng IP không mà không cần SSH vào AP.

## 5. Verification & Inspection Patterns

### A. Swarm API Inspection (`opcode=show`)
* **Master vs. Slave Query Behavior:** Running `show aps` against a Slave AP returns `<t tn="0 Access Point">`. To view all cluster APs and their client allocations, either:
  1. Read `show summary` on any AP to extract `Master IP Address` (marked with `*`), then send `show aps` directly to the Master IP.
  2. Or read `show ap bss-table` or `show clients` which are populated on all nodes.

```python
# 1. Show all APs and their current zone, clients, channels (Execute against Master IP)
show_aps_xml = aruba_show(master_ip, sid, "show aps")

# 2. Show all SSID profiles and active status
show_network_xml = aruba_show(ip, sid, "show network")

# 3. Show cluster summary and Master AP IP
show_summary_xml = aruba_show(ip, sid, "show summary")
```

### B. SSH Automation via Interactive PTY (Paramiko)
* **Quirk:** Older Aruba InstantOS drops non-interactive `exec_command()` calls with `Channel closed`, and native `ssh` CLI hangs on password prompts.
* **Working Pattern:** Use `paramiko.SSHClient` with `invoke_shell()`:
```python
import paramiko, time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(ip, username="admin", password="n0spam@@", timeout=3, allow_agent=False, look_for_keys=False)
chan = ssh.invoke_shell()
time.sleep(1)
chan.send("show aps\n")
time.sleep(2)
output = chan.recv(65535).decode("utf-8", errors="ignore")
ssh.close()
```
