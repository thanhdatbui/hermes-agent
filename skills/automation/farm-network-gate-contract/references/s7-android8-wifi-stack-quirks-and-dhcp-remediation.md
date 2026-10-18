# Samsung Galaxy S7 (Android 8) Wi-Fi Stack Quirks & DHCP Remediation

## 1. Incident Overview (Máy 7 Farm Case Study)

During the deployment of `farm_network_gate.py` on Máy 7 (serial `9885f63030454d3055`, Galaxy S7 Android 8), the device initially failed with `L2_AUTH_FAIL`, then progressed to `L3_NO_IP`. Investigation uncovered four specific low-level quirks of the Samsung S7 Android 8 networking stack that cause gate false-positives and connection hangs if not handled mechanically.

---

## 2. Low-Level Quirks & Root Causes

### A. Stale Profile Accumulation & Blacklisted Networks (ID >= 10)
- **Symptom:** Even when supplied with the correct WPA2 passphrase (`23102025` for `kibe 1`), the device immediately returned `DISCONNECTED` or failed association.
- **Root Cause:** In Android 8, networks are assigned incremental integer IDs. Prior ad-hoc join attempts had accumulated network profiles up to `ID: 10` and `ID: 11`. In `dumpsys wifi`:
  ```text
  ID: 10 SSID: "kibe 1"
  NetworkSelectionStatus NETWORK_SELECTION_TEMPORARY_DISABLED
  mNetworkSelectionDisableReason NETWORK_SELECTION_DISABLED_AUTHENTICATION_FAILURE
  blackListed: 1792271717sec  cuid=10179 cname=com.steinwurf.adbjoinwifi
  ```
  The old cleanup logic only swept `STALE_NETWORK_IDS = range(10)`. Network 10 remained untouched and blacklisted by the OS supplicant, preventing new connection attempts to `kibe 1`.
- **Remediation:**
  ```python
  def _forget_all_networks(serial: str):
      text = _adb_shell(serial, "dumpsys wifi").stdout or ""
      ids = {int(x) for x in re.findall(r"ID:\s*(\d+)", text)}
      for i in sorted(set(range(30)) | ids):
          _adb_shell(serial, f"service call wifi 14 i32 {i}")
  ```

---

### B. Non-Root Socket Failure on `ping -I wlan0`
- **Symptom:** L3 gateway verification reported `gateway unreachable` even when the Wi-Fi link was up.
- **Root Cause:** On Samsung Android 8 without root privileges, passing `-I wlan0` to `ping` (`ping -c 1 -W 3 -I wlan0 192.168.110.1`) fails with returncode `2` (`connect: Network is unreachable` or socket `Permission denied`) because binding to a network interface requires `CAP_NET_RAW` / root capabilities.
- **Remediation:**
  1. Attempt standard ICMP ping without `-I`: `ping -c 1 -W 2 <GATEWAY>`.
  2. If ICMP is blocked or returns non-zero, fallback to TCP probe on Gateway port 80:
     `toybox nc -w 3 -W 3 <GATEWAY> 80 < /dev/null`.
  3. If Gateway port 80 is closed to clients, fallback to TCP probe on Sing-box proxy port (`192.168.110.2:200xx`). If any LAN host on the subnet responds to TCP, L3 routing is verified.

---

### C. Incompatible Netcat Flags on Toybox (`-z` Unsupported)
- **Symptom:** Port probe commands crashed or returned syntax errors.
- **Root Cause:** Android 8 uses `toybox` as its shell core utility provider. Unlike BSD netcat, `toybox nc` does NOT support the `-z` flag (zero-I/O scanning).
- **Remediation:** Use standard timeout flags with input redirection:
  ```python
  def _proxy_open(serial: str, host: str, port: int) -> bool:
      r = _adb_shell(serial, f"toybox nc -w 3 -W 3 {host} {port} < /dev/null", timeout=15)
      return r.returncode == 0
  ```

---

### D. Post-WPA2 Association DHCP Stall
- **Symptom:** The WPA2 4-way handshake completes successfully:
  ```text
  14: wlan0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 state UP
      link/ether ac:5f:3e:60:59:1b
      inet6 fe80::ae5f:3eff:fe60:591b/64 scope link
  ```
  However, no IPv4 address is assigned (`ip addr show wlan0` shows only link-local IPv6).
- **Root Cause:** Android 8's DHCP client daemon (`DhcpClient`) occasionally stalls or misses the router's DHCP Offer after rapid radio toggling.
- **Remediation Hierarchy:**
  1. Trigger DHCP renewal via ADB:
     ```python
     def _renew_dhcp(serial: str):
         _adb_shell(serial, "dhcpcd -n wlan0")
         _adb_shell(serial, "svc wifi disable")
         _adb_shell(serial, "sleep 1")
         _adb_shell(serial, "svc wifi enable")
     ```
  2. Increase poll budget: `IP_POLL_ATTEMPTS = 10`, `IP_POLL_INTERVAL = 2.0s` (total 20s).
  3. If DHCP server fails to respond, fallback to assigning the known static IP mapped for the machine (e.g. `192.168.110.124/24` with default gateway `192.168.110.1`).

---

## 3. Operator Mandate: Anti-Paralysis Protocol (No Passive BLOCKED)

- **User Correction (2026-10-18):** *"TAO CĂM THÙ CHỮ BLOCKED... làm việc mà cứ dừng lại khóc"*.
- **Invariant:** A Coordinator MUST NEVER passively report `BLOCKED` and stop working when encountering a gate failure or network block.
- **Required Behavior:**
  1. Inspect physical device state immediately using $O(1)$ inspect tools (`inspect_machine.py`, `dumpsys wifi`, `ip addr show wlan0`).
  2. Isolate the exact physical layer failure (L2 WPA2 vs L3 DHCP vs L4 Proxy).
  3. Formulate and propose/execute deterministic remediation (e.g. DHCP renewal, static IP fallback, or full network ID flush).
