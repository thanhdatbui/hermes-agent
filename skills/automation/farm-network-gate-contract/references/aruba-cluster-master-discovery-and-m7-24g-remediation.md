# Aruba Cluster Master Discovery & Pure 2.4GHz Wi-Fi Remediation for Degraded Hardware

## 1. Context & Incident Summary
- **Device:** Machine 7 (Galaxy S7 `SM-G930F`, serial `9885f63030454d3055`).
- **Symptom:** M7 was assigned to SSID `Dat` (password `19051995`) after failing on `kibe 1` 5GHz. However, feed session watchdog still reported `Mất kết nối Wi-Fi (AP)` / `dumpsys connectivity: Wi-Fi not connected`.
- **Underlying Cause:** SSID `Dat` was configured as Dual-Band (`rf-band all` = 2.4GHz + 5GHz). Samsung Android 8's `SavedNetworkEvaluator` automatically awards a `+40` bonus score to 5GHz BSSIDs (`5GHz bonus: 40`). Because M7 has a degraded 5GHz RF chip/antenna, the Aruba AP rejects association (`ASSOCIATION_REJECTION status=1`). After 8 repeated rejections, Android framework permanently disables the entire SSID:
  `Disabled saved networks: "Dat" reason=NETWORK_SELECTION_DISABLED_ASSOCIATION_REJECTION counter:8`.
  Once blacklisted, Android refuses to connect even to the healthy 2.4GHz radio of `Dat`.

---

## 2. Aruba Instant Cluster Master Discovery
In a multi-AP Aruba Instant cluster (`192.168.110.250`–`253`), the Virtual Controller (VC Master) can dynamically migrate or failover between APs.
- **Symptom of contacting a non-master AP:** API calls to `https://<ip>:4343/swarm.cgi` succeed at `opcode: login`, but any subsequent `show` or `config` command immediately returns:
  ```xml
  <?xml version='1.0'?><re><error>Invalid Session ID</error></re>
  ```
- **Discovery Protocol:** Probe all cluster IPs to find the active VC Master:
  ```python
  import urllib.request, ssl, urllib.parse, random, xml.etree.ElementTree as ET

  ctx = ssl.create_default_context()
  ctx.check_hostname = False
  ctx.verify_mode = ssl.CERT_NONE
  headers = {'User-Agent': 'Mozilla/5.0', 'X-Requested-With': 'XMLHttpRequest', 'Content-Type': 'application/x-www-form-urlencoded'}

  for ip in ['192.168.110.253', '192.168.110.252', '192.168.110.251', '192.168.110.250']:
      try:
          payload = {'opcode': 'login', 'nosid': 'true', 'user': 'admin', 'passwd': 'n0spam@@', 'nocache': str(random.random())}
          req = urllib.request.Request(f'https://{ip}:4343/swarm.cgi', data=urllib.parse.urlencode(payload).encode(), headers=headers)
          body = urllib.request.urlopen(req, context=ctx, timeout=3).read().decode('utf-8')
          sid = ET.fromstring(body).find("data[@name='sid']").text

          p = {'opcode': 'show', 'sid': sid, 'cmd': 'show aps', 'nocache': str(random.random())}
          r = urllib.request.Request(f'https://{ip}:4343/swarm.cgi', data=urllib.parse.urlencode(p).encode(), headers=headers)
          out = urllib.request.urlopen(r, context=ctx, timeout=3).read().decode('utf-8')
          if 'Access Points' in out:
              print(f"ACTIVE VC MASTER FOUND: {ip}")
              break
      except Exception:
          pass
  ```
  *Note:* The active Master returns `<t tn="4 Access Points" ...>`, while member APs return `<t tn="0 Access Point" ...>` or invalid session.

---

## 3. Creating Pure 2.4GHz SSID Profile on Aruba (VLAN 1 & Access Rule Invariant)
Send the configuration payload directly to the active VC Master.

> **CRITICAL PITFALL — L3_NO_IP TRAP:**
> By default, newly created SSID profiles on Aruba Instant have no VLAN assignment (`Default VLAN` / NULL) and their access-rule defaults to `DENY ALL` (`rule any any match any any any deny`).
> If `vlan 1` and `permit` access-rule are omitted, the phone successfully associates at L2 (WPA2 handshake OK), but Aruba drops all DHCP Discover packets, causing `L3_NO_IP` (`raw_wlan0: `).
> You MUST configure both `vlan 1` and `rule any any match any any any permit` in the config script:

```text
wlan ssid-profile Dat_2.4G
enable
essid "Dat_2.4G"
wpa-passphrase 19051995
opmode wpa2-psk-aes
rf-band 2.4
vlan 1
broadcast-filter arp
zone zone1,zone2,zone3,zone4
exit
wlan access-rule Dat_2.4G
rule any any match any any any permit
exit
```
- `rf-band 2.4`: Ensures the SSID is broadcast ONLY on 2.4GHz radios. Phones cannot see or attempt 5GHz connections, eliminating the `+40` bonus trap.
- `vlan 1`: Bridges Wi-Fi client traffic directly to Farm LAN / Ruijie Gateway DHCP pool (`192.168.110.0/24`).
- `wlan access-rule ... permit`: Replaces default ACL `deny` with unrestricted LAN/WAN traffic forwarding.
- `broadcast-filter arp`: Prevents ARP broadcast storms across the farm.
- `zone zone1,zone2,zone3,zone4`: Allows all 4 APs across the room to broadcast the recovery SSID.

Verify profile creation with:
```python
p = {'opcode': 'show', 'sid': sid, 'cmd': 'show network Dat_2.4G', 'nocache': str(random.random())}
```
Expect: `Status: Enabled`, `Band: 2.4`, `VLAN: 1`, `Active: Yes`, `Access Rules: any any permit`.

---

## 4. SSOT Configuration & Device Rollout
1. Update `D:/Taadaa/machine-config/farm_wifi_profiles.json`:
   ```json
   {
     "min": 7,
     "max": 7,
     "ssid": "Dat_2.4G",
     "password": "19051995"
   }
   ```
2. Execute the canonical farm gate under device lock:
   ```bash
   python D:/Taadaa/tools/farm_network_gate.py 7 9885f63030454d3055 --force-preempt
   ```
   *Timeout note:* Foreground commands on this host have a hard 60s cap. Because `_join_wifi` + DHCP evaluation takes ~55-75s total, invoke via `background=True` with `notify_on_complete=True`.

---

## 5. Coordinator vs Worker CLI Role Boundary (Anti-Disruption Rule)
- **Code-Fix Worker CLI (`dispatch_worker.py`):** Runs under strict tool lock (`allowedTools: Read,Edit`). It rejects operational runbooks that touch live network APIs, device locks, or system commands (`BLOCKED: operational runbook not permitted`).
- **Rule:** Never delegate live farm operational runbooks (Aruba API, device locks, Wi-Fi joins) to Code-Fix Worker CLI. Execute directly via Coordinator tools or canonical gate scripts.

---

## 6. Device Bulkhead vs Screencap Evidence Pitfall (`GUARD_DEVICE_LOCK_REQUIRED`)
- **Symptom:** Running raw ADB commands such as `adb -s <serial> exec-out screencap -p > screen.png` from terminal is immediately blocked by `COORDINATOR TERMINAL BLOCKED (DEFAULT-DENY)` with rule `GUARD_DEVICE_LOCK_REQUIRED`.
- **Underlying Mechanism:** `guard_device_bulkhead.py` intercepts any terminal command touching an Android device if the caller does not hold an active `operator_device_lock` lease file.
- **Evidence Verification Domain Distinction:**
  * **Gate 6 (UI Visual Screenshot Invariant):** Strictly applies to user-facing or app automation (TikTok app, GPM browser, Settings UI interactions, Form filling, Click actions) where visual layout state must be verified via screenshot prior to claiming success.
  * **Network Infrastructure Domain (L2-L4 Gates):** For Wi-Fi profile provisioning, AP configuration, IP allocation, and proxy attachment, proof of record is established via:
    1. L2: Virtual Controller association table (`show clients` on active VC Master proving BSSID, band, signal).
    2. L3: `ip addr show wlan0` confirming subnet IP via `farm_network_gate.py` (which internally manages the device lock).
    3. L4: TCP socket probe (`toybox nc` to proxy host/port).
  * If a screenshot is truly required, it must be captured *inside* the script holding the `operator_device_lock`, never via naked terminal ADB commands.

---

## 7. Anti-Freezing & Heartbeat Invariant (Anti-Silent-Wait)
- **Rule:** Never leave the operator in a silent loop or uncommunicative state while waiting for a background process (e.g. `dispatch_worker`, `farm_network_gate`).
- If a background worker terminates or fails, Coordinator must immediately react in the very next turn, inspect the failure, and pivot directly rather than leaving the session appearing frozen or hanging for extended intervals.
