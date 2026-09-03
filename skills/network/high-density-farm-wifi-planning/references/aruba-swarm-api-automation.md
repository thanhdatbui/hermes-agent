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

## 5. Verification Commands
```python
# Show all APs and their current zone, clients, channels
show_aps_xml = aruba_config(ip, sid, "show aps")

# Show all SSID profiles and active status
show_network_xml = aruba_config(ip, sid, "show network")
```
